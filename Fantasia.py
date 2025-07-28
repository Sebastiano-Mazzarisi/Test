# Script per estrarre l'immagine del "Menù del giorno" dalla pagina Facebook
# di Rosticceria Fantasia, convertire l'immagine in testo tramite OCR e
# inviare il testo via email e/o via WhatsApp.
#
# VERSIONE CORRETTA:
# Include una logica di controllo per evitare l'invio di menù duplicati.
# Utilizza un file 'status.json' per "ricordare" l'ultimo menù inviato.

from __future__ import annotations

import os
import datetime
import re
import time
import traceback
import json
import hashlib
from typing import Iterable, Optional

import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from PIL import Image
import pytesseract  # type: ignore
from facebook_scraper import get_posts  # type: ignore
import schedule  # type: ignore

try:
    from twilio.rest import Client  # type: ignore
except ImportError:
    Client = None

# --- CONFIGURAZIONE ---
PAGE_NAME = "RosticceriaFantasia"
TARGET_PHRASE = "MENÙ DEL GIORNO"
RECIPIENT_EMAIL = "s.mazzarisi@mazzarisi.it"
COOKIES_FILE = "cookies.txt"
STATUS_FILE = "status.json" # File per memorizzare lo stato dell'ultimo invio

# Credenziali per email e WhatsApp da impostare come variabili d'ambiente:
# EMAIL_USER, EMAIL_PASS
# TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO


def debug_log(message: str) -> None:
    """Stampa i messaggi di debug con timestamp."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}")


def fetch_menu_post(pages_to_scan: int = 10, cookies: Optional[str] = None) -> Optional[dict]:
    """
    Scansiona i post recenti della pagina Facebook per trovare il post
    del menù del giorno.
    """
    debug_log(f"Ricerca del post con '{TARGET_PHRASE}' su {PAGE_NAME}...")
    options = {"allow_extra_requests": True}
    try:
        posts: Iterable[dict] = get_posts(
            PAGE_NAME,
            pages=pages_to_scan,
            cookies=cookies,
            options=options,
        )
        for post in posts:
            post_text = post.get('text', '').upper()
            # Cerca il post corretto e assicurati che abbia un'immagine
            if TARGET_PHRASE in post_text and (post.get("image") or post.get("images")):
                debug_log("Trovato il post del menù del giorno.")
                return post
    except Exception as exc:
        debug_log(f"Errore durante lo scraping della pagina: {exc}")
        traceback.print_exc()
    return None


def download_image(image_url: str, destination: str) -> bool:
    """Scarica l'immagine dall'URL specificato."""
    debug_log(f"Download dell'immagine: {image_url}")
    try:
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        with open(destination, "wb") as f:
            f.write(response.content)
        return True
    except Exception as exc:
        debug_log(f"Impossibile scaricare l'immagine: {exc}")
        return False


def extract_text_from_image(image_path: str) -> str:
    """Utilizza Tesseract per estrarre testo da un'immagine."""
    debug_log(f"Avvio OCR sull'immagine: {image_path}")
    try:
        with Image.open(image_path) as img:
            gray = img.convert("L")
            bw = gray.point(lambda x: 255 if x > 150 else 0, mode="1") # Soglia ottimizzata
            text = pytesseract.image_to_string(bw, lang="ita")
            return text.strip()
    except Exception as exc:
        debug_log(f"Errore OCR: {exc}")
        return ""


def send_email(subject: str, body: str, recipient: str = RECIPIENT_EMAIL) -> bool:
    """Invia una mail utilizzando le credenziali definite nelle variabili d'ambiente."""
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    if not sender or not password:
        debug_log("Credenziali email non configurate. Impossibile inviare.")
        return False
        
    debug_log(f"Invio email a {recipient}...")
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    try:
        smtp_server = "smtp.gmail.com"
        port = 587
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        debug_log("Email inviata con successo.")
        return True
    except Exception as exc:
        debug_log(f"Impossibile inviare l'email: {exc}")
        return False


def send_whatsapp(body: str) -> bool:
    """Invia un messaggio WhatsApp utilizzando Twilio."""
    if Client is None:
        debug_log("Libreria Twilio non installata. Salto invio WhatsApp.")
        return False
        
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_wa = os.getenv("TWILIO_WHATSAPP_FROM")
    to_wa = os.getenv("TWILIO_WHATSAPP_TO")

    if not all([sid, token, from_wa, to_wa]):
        debug_log("Parametri Twilio non configurati. Impossibile inviare.")
        return False
        
    debug_log(f"Invio messaggio WhatsApp a {to_wa}...")
    try:
        client = Client(sid, token)
        client.messages.create(body=body, from_=from_wa, to=to_wa)
        debug_log("Messaggio WhatsApp inviato con successo.")
        return True
    except Exception as exc:
        debug_log(f"Impossibile inviare il messaggio WhatsApp: {exc}")
        return False


def show_popup(message: str) -> None:
    """Visualizza un popup con il testo del menù (fallback)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Menù del giorno", message)
        root.destroy()
    except Exception:
        debug_log(f"Impossibile mostrare popup. Testo:\n{message}")


def process_daily_menu() -> None:
    """
    Funzione principale che orchestra l'intero processo, con logica
    per evitare invii duplicati.
    """
    debug_log(f"Avvio processo per il {datetime.date.today().isoformat()}")

    # 1. Carica lo stato precedente
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        status = {"last_sent_date": "", "last_menu_hash": ""}

    # Cerca il post del menù
    cookies_path = COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    post = fetch_menu_post(pages_to_scan=10, cookies=cookies_path)
    if not post:
        debug_log("Nessun post del menù trovato. Fine del processo.")
        return

    # Estrai l'URL dell'immagine e scaricala
    image_url = post.get("image") or (post.get("images", [])[0] if post.get("images") else None)
    if not image_url:
        debug_log("Post trovato ma non contiene immagini. Fine del processo.")
        return
    
    image_path = "menu_del_giorno.jpg"
    if not download_image(image_url, image_path):
        debug_log("Download dell'immagine fallito. Fine del processo.")
        return

    # Estrai il testo dall'immagine
    text = extract_text_from_image(image_path)
    if not text:
        debug_log("Testo OCR vuoto. Fine del processo.")
        return

    # 2. Genera l'hash del menù attuale
    current_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

    # 3. Controlla se il menù è nuovo
    if current_hash != status.get("last_menu_hash"):
        debug_log(f"Nuovo menù rilevato (hash: {current_hash[:7]}...). Invio notifiche.")
        
        today = datetime.date.today()
        subject_line = f"Menù del giorno {today.strftime('%d/%m/%Y')}"
        
        email_ok = send_email(subject_line, text)
        wa_ok = send_whatsapp(text)

        # 4. Aggiorna lo stato solo dopo un invio andato a buon fine
        if email_ok or wa_ok:
            status['last_sent_date'] = today.isoformat()
            status['last_menu_hash'] = current_hash
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=4)
            debug_log("File di stato aggiornato con successo.")
        else:
            debug_log("Invio fallito. Lo stato non è stato aggiornato.")
            if not os.getenv("EMAIL_USER") and not os.getenv("TWILIO_ACCOUNT_SID"):
                 show_popup(text) # Fallback con popup se nessuna notifica è configurata
    else:
        debug_log("Il menù non è cambiato dall'ultimo invio. Nessuna azione.")


def schedule_daily_task(hour: str = "10:00") -> None:
    """Pianifica l'esecuzione giornaliera."""
    debug_log(f"Pianificazione del task giornaliero alle {hour}")
    schedule.every().day.at(hour).do(process_daily_menu)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    # Esegue subito il processo una volta per test/debug
    process_daily_menu()
    
    # Avvia la pianificazione giornaliera (decommentare per l'uso in produzione)
    # debug_log("Avvio della pianificazione giornaliera...")
    # schedule_daily_task("10:00")