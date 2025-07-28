# Script per estrarre l'immagine del "Menù del giorno" dalla pagina Facebook
# e inviarla via email (come allegato) e/o via WhatsApp (come link).
#
# VERSIONE SENZA OCR:
# Non esegue il riconoscimento del testo, invia solo l'immagine.
# Il controllo duplicati è basato sull'hash del file immagine.

from __future__ import annotations

import os
import datetime
import json
import hashlib
import traceback
from typing import Iterable, Optional

import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import smtplib

from facebook_scraper import get_posts
import schedule

try:
    from twilio.rest import Client
except ImportError:
    Client = None

# --- CONFIGURAZIONE ---
PAGE_NAME = "RosticceriaFantasia"
TARGET_PHRASE = "MENÙ DEL GIORNO"
RECIPIENT_EMAIL = "s.mazzarisi@mazzarisi.it"
COOKIES_FILE = "cookies.txt"
STATUS_FILE = "status.json"

# Credenziali per email e WhatsApp da impostare come variabili d'ambiente.


def debug_log(message: str) -> None:
    """Stampa i messaggi di debug con timestamp."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}")


def fetch_menu_post(pages_to_scan: int = 10, cookies: Optional[str] = None) -> Optional[dict]:
    """Scansiona i post recenti per trovare il post del menù del giorno."""
    debug_log(f"Ricerca del post con '{TARGET_PHRASE}' su {PAGE_NAME}...")
    options = {"allow_extra_requests": True}
    try:
        for post in get_posts(PAGE_NAME, pages=pages_to_scan, cookies=cookies, options=options):
            post_text = post.get('text', '').upper()
            if TARGET_PHRASE in post_text and (post.get("image") or post.get("images")):
                debug_log("Trovato il post del menù del giorno.")
                return post
    except Exception as exc:
        debug_log(f"Errore durante lo scraping: {exc}")
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


def send_email_with_attachment(subject: str, body_text: str, image_path: str, recipient: str = RECIPIENT_EMAIL) -> bool:
    """Invia un'email con un'immagine come allegato."""
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    if not sender or not password:
        debug_log("Credenziali email non configurate.")
        return False

    debug_log(f"Invio email con allegato a {recipient}...")
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    try:
        with open(image_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
            msg.attach(img)
    except FileNotFoundError:
        debug_log(f"Immagine non trovata in {image_path}, impossibile allegarla.")
        return False

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        debug_log("Email con allegato inviata con successo.")
        return True
    except Exception as exc:
        debug_log(f"Impossibile inviare l'email: {exc}")
        return False


def send_whatsapp_with_image_url(body: str, image_url: str) -> bool:
    """Invia un messaggio WhatsApp con un link a un'immagine."""
    if Client is None:
        return False
    
    sid, token, from_wa, to_wa = (os.getenv(k) for k in ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "TWILIO_WHATSAPP_TO"])
    if not all([sid, token, from_wa, to_wa]):
        debug_log("Parametri Twilio non configurati.")
        return False
        
    debug_log(f"Invio messaggio WhatsApp a {to_wa}...")
    try:
        client = Client(sid, token)
        client.messages.create(body=body, from_=from_wa, to=to_wa, media_url=[image_url])
        debug_log("Messaggio WhatsApp inviato con successo.")
        return True
    except Exception as exc:
        debug_log(f"Impossibile inviare il messaggio WhatsApp: {exc}")
        return False


def process_daily_menu() -> None:
    """Funzione principale che orchestra il processo."""
    debug_log(f"Avvio processo per il {datetime.date.today().isoformat()}")
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        status = {"last_menu_hash": ""}

    cookies_path = COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    post = fetch_menu_post(cookies=cookies_path)
    if not post:
        debug_log("Nessun post del menù trovato.")
        return

    image_url = post.get("image") or (post.get("images", [])[0] if post.get("images") else None)
    if not image_url:
        debug_log("Post trovato ma senza immagine.")
        return
    
    image_path = "menu_del_giorno.jpg"
    if not download_image(image_url, image_path):
        return

    # Crea l'hash del file immagine
    with open(image_path, 'rb') as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()

    if current_hash != status.get("last_menu_hash"):
        debug_log(f"Nuova immagine rilevata (hash: {current_hash[:7]}...).")
        
        today_str = datetime.date.today().strftime('%d/%m/%Y')
        subject = f"Menù del giorno {today_str}"
        body = f"Ecco il menù del giorno {today_str} dalla Rosticceria Fantasia."

        email_ok = send_email_with_attachment(subject, body, image_path)
        wa_ok = send_whatsapp_with_image_url(body, image_url)

        if email_ok or wa_ok:
            status['last_menu_hash'] = current_hash
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=4)
            debug_log("File di stato aggiornato.")
    else:
        debug_log("L'immagine del menù non è cambiata dall'ultimo invio.")

if __name__ == "__main__":
    process_daily_menu()