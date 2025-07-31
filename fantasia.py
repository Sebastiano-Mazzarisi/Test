# ==============================================================================
#      SCRIPT FINALE PER GITHUB ACTIONS (LETTO DA VARIABILE D'AMBIENTE)
#
#                         -- VERSIONE 9.2 CON CONTROLLO ORARIO --
#
# OBIETTIVO: Essere eseguito in modo automatico e sicuro su GitHub Actions.
#            La password dell'email viene letta da un "Secret" di GitHub.
#            NUOVO: Controllo orario programmato dalle 09:00 alle 12:00
# ==============================================================================

CONFIG = {
    # Configurazione Scraping
    "FACEBOOK_PAGE": "RosticceriaFantasia",
    "TARGET_KEYWORDS": ["MENU DEL GIORNO", "MENÙ DEL GIORNO", "IL NOSTRO MENU", "MENU DI OGGI"],
    "COOKIE_FILE": "cookies.txt",
    "OUTPUT_DIR": "output",
    "LOG_FILE": "output/menu_extractor.log",

    # Configurazione Email
    "EMAIL_SENDER_ADDRESS": "s.mazzarisi@gmail.com",
    
    # La password viene letta da un Secret di GitHub, non più scritta qui.
    "EMAIL_SENDER_PASSWORD": "",
    
    "EMAIL_RECIPIENT_ADDRESS": "s.mazzarisi@mazzarisi.it",
    "EMAIL_SMTP_SERVER": "smtp.gmail.com",
    "EMAIL_SMTP_PORT": 587,
    
    # MODALITÀ TEST: Se True, invia il primo post con immagine trovato
    "TEST_MODE": False,
    
    # CONFIGURAZIONE ORARIO
    "MONITORING_START_HOUR": 8,   # Ora di inizio monitoraggio
    "MONITORING_END_HOUR": 12,    # Ora di fine monitoraggio
    "CHECK_INTERVAL_MINUTES": 10, # Intervallo controlli in minuti
}

# ==============================================================================
# =================== FINE CONFIGURAZIONE - NON MODIFICARE SOTTO ===============
# ==============================================================================

import os
import sys
import datetime
import logging
import time
import argparse
import requests
import html
from typing import Dict, Optional, List

# Import per le email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    import schedule
except ImportError as e:
    print(f"ERRORE: Manca una libreria fondamentale -> {e.name}.")
    print("Esegui 'pip install playwright schedule requests Pillow' e poi 'playwright install'")
    sys.exit(1)

def setup_logging(log_path: str):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s",
                        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler(sys.stdout)])

class NotificationManager:
    def __init__(self, config: dict):
        self.config = config

    def send_menu_image(self, image_path: str, post_text: str = ""):
        sender, password, recipient = self.config.get("EMAIL_SENDER_ADDRESS"), self.config.get("EMAIL_SENDER_PASSWORD"), self.config.get("EMAIL_RECIPIENT_ADDRESS")
        if not all([sender, password, recipient]): return logging.error("Credenziali email non configurate o password mancante.")
        
        logging.info(f"Preparo l'email HTML pulita per {recipient}...")
        try:
            msg = MIMEMultipart('related')
            test_suffix = " [MODALITÀ TEST]" if self.config.get("TEST_MODE") else ""
            msg['Subject'] = f"Rosticceria Fantasia{test_suffix}"
            msg['From'], msg['To'] = sender, recipient
            cleaned_text = html.escape(post_text)
            html_body = f"""
            <html><head></head><body style="font-family: sans-serif;">
            <pre style="font-family: sans-serif; font-size: 1em; white-space: pre-wrap; word-wrap: break-word;">{cleaned_text}</pre>
            <img src="cid:menu_image">
            </body></html>"""
            msg.attach(MIMEText(html_body, 'html'))
            with open(image_path, 'rb') as f:
                img = MIMEImage(f.read())
            img.add_header('Content-ID', '<menu_image>')
            msg.attach(img)
            logging.info(f"Invio email a {recipient}...")
            with smtplib.SMTP(self.config["EMAIL_SMTP_SERVER"], self.config["EMAIL_SMTP_PORT"]) as server:
                server.starttls(); server.login(sender, password); server.sendmail(sender, recipient, msg.as_string())
            logging.info("✅ Email inviata con successo!")
        except Exception as e: logging.error(f"❌ Fallimento invio email: {e}")

class FacebookScraper:
    def __init__(self, page_name: str, cookie_file_path: str):
        self.page_url = f"https://www.facebook.com/{page_name}"
        self.cookie_file_path = cookie_file_path
        
    def _load_cookies_for_playwright(self) -> Optional[List[Dict]]:
        if not os.path.exists(self.cookie_file_path): logging.error(f"File cookie '{self.cookie_file_path}' non trovato."); return None
        cookies = []
        with open(self.cookie_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 7: cookies.append({'domain': parts[0], 'path': parts[2], 'secure': parts[3].upper() == 'TRUE', 'expires': int(parts[4]), 'name': parts[5], 'value': parts[6], 'httpOnly': False, 'sameSite': 'Lax'})
        if not any('.facebook.com' in c['domain'] for c in cookies): logging.error("Nessun cookie di Facebook trovato nel file."); return None
        logging.info(f"Caricati {len(cookies)} cookie validi."); return cookies
    
    def find_daily_menu_post(self, keywords: List[str], test_mode: bool = False) -> Optional[Dict]:
        logging.info(f"Avvio scraping con Playwright per '{self.page_url}'...")
        if test_mode:
            logging.info("🧪 MODALITÀ TEST: Cercherò il primo post con immagine, ignorando le keywords")
        
        # Aggiungi timestamp alle keywords per renderle sempre diverse
        current_time = datetime.datetime.now().strftime("%H%M%S")
        modified_keywords = [f"{current_time} {keyword}" for keyword in keywords]
        
        logging.info(f"Keywords di ricerca: {modified_keywords if not test_mode else 'MODALITÀ TEST - qualsiasi post con immagine'}")
        
        cookies = self._load_cookies_for_playwright()
        if not cookies: return None
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36')
                context.add_cookies(cookies)
                page = context.new_page()
                page.goto(self.page_url, wait_until='load', timeout=60000)
                time.sleep(5)
                posts = page.locator('div[aria-posinset]').all() or page.locator('div[role="article"]').all()
                logging.info(f"Trovati {len(posts)} post candidati.")
                
                for post_element in posts[:15]:
                    post_full_text = post_element.inner_text()
                    
                    # In modalità test, accetta qualsiasi post con immagine
                    if test_mode:
                        keywords_match = True
                    else:
                        # Usa le keywords originali (senza timestamp) per la ricerca
                        keywords_match = any(keyword.upper() in post_full_text.upper() for keyword in keywords)
                    
                    if keywords_match:
                        image_loc = post_element.locator('a[href*="photo"] img, img[data-visualcompletion="media-vc-image"]').first
                        if image_loc.is_visible(timeout=5000):
                            image_url = image_loc.get_attribute('src')
                            text_content_loc = post_element.locator('div[data-ad-preview="message"], div:has(> span[dir="auto"])').first
                            post_text_content = text_content_loc.inner_text() if text_content_loc.count() > 0 else ""
                            
                            if test_mode:
                                logging.info("🧪 TEST: Post con immagine trovato!")
                                post_text_content = f"[TEST MODE - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}]\n\n{post_text_content}"
                            else:
                                logging.info("🎉 Post del menù trovato!")
                            
                            browser.close()
                            return {'image': image_url, 'text': post_text_content}
                
                browser.close(); return None
            except Exception as e:
                logging.error(f"Errore scraping Playwright: {e}")
                if browser and browser.is_connected(): browser.close()
                return None

class ImageProcessor:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir; os.makedirs(output_dir, exist_ok=True)
        
    def download_image(self, post_data: Dict) -> Optional[str]:
        image_url = post_data.get("image")
        if not image_url: return logging.error("URL immagine non trovato."), None
        try:
            response = requests.get(image_url, timeout=30); response.raise_for_status()
            filepath = os.path.join(self.output_dir, f"menu_{datetime.date.today().strftime('%Y%m%d')}.jpg")
            with open(filepath, 'wb') as f: f.write(response.content)
            logging.info(f"Immagine scaricata: {filepath}")
            return filepath
        except requests.RequestException as e: return logging.error(f"Errore download: {e}"), None

class MenuExtractor:
    def __init__(self, config: dict):
        # Legge la password dal Secret di GitHub (variabile d'ambiente)
        config["EMAIL_SENDER_PASSWORD"] = os.getenv('GMAIL_APP_PASSWORD', config.get("EMAIL_SENDER_PASSWORD"))
        
        # Attiva modalità test se specificato tramite variabile d'ambiente
        config["TEST_MODE"] = os.getenv('TEST_MODE', 'false').lower() == 'true'
        
        self.config = config
        self.scraper = FacebookScraper(config["FACEBOOK_PAGE"], config["COOKIE_FILE"])
        self.processor = ImageProcessor(config["OUTPUT_DIR"])
        self.notifier = NotificationManager(config)
        self.menu_sent_today = False  # Flag per evitare invii multipli
        self.last_check_date = None   # Traccia l'ultimo giorno di controllo

    def is_monitoring_time(self) -> bool:
        """Controlla se siamo nell'orario di monitoraggio"""
        now = datetime.datetime.now().time()
        start_time = datetime.time(self.config["MONITORING_START_HOUR"], 0)
        end_time = datetime.time(self.config["MONITORING_END_HOUR"], 0)
        return start_time <= now <= end_time

    def reset_daily_flag_if_needed(self):
        """Resetta il flag giornaliero se è un nuovo giorno"""
        today = datetime.date.today()
        if self.last_check_date != today:
            self.menu_sent_today = False
            self.last_check_date = today
            logging.info(f"🗓️  Nuovo giorno: {today.strftime('%d/%m/%Y')} - Flag reset")

    def run_full_flow(self):
        """Esegue il flusso completo di estrazione menu"""
        test_mode = self.config.get("TEST_MODE", False)
        if test_mode:
            logging.info("🧪 --- MODALITÀ TEST ATTIVATA ---")
        
        # Controlla se abbiamo già inviato il menu oggi
        self.reset_daily_flag_if_needed()
        if self.menu_sent_today and not test_mode:
            logging.info("📧 Menu già inviato oggi. Salto l'estrazione.")
            return
        
        logging.info("--- Inizio Flusso Estrazione Menu ---")
        post = self.scraper.find_daily_menu_post(self.config["TARGET_KEYWORDS"], test_mode)
        if not post: 
            logging.info("🔍 Post non trovato in questo controllo.")
            return
        
        image_path = self.processor.download_image(post)
        if not image_path: 
            logging.error("Processo interrotto: download fallito.")
            return
        
        self.notifier.send_menu_image(image_path, post.get("text", ""))
        self.menu_sent_today = True  # Marca come inviato
        logging.info("--- Flusso Completato con Successo ---")

    def run_scheduled_monitoring(self):
        """Monitora la pagina Facebook dalle 09:00 alle 12:00"""
        start_hour = self.config["MONITORING_START_HOUR"]
        end_hour = self.config["MONITORING_END_HOUR"]
        check_interval = self.config["CHECK_INTERVAL_MINUTES"]
        
        logging.info(f"🕘 Avvio monitoraggio programmato ({start_hour:02d}:00-{end_hour:02d}:00)")
        logging.info(f"⏰ Controllo ogni {check_interval} minuti")
        
        # Programma il controllo periodico
        schedule.every(check_interval).minutes.do(self._scheduled_check)
        
        while True:
            try:
                current_time = datetime.datetime.now()
                
                if self.is_monitoring_time():
                    # Siamo nell'orario di monitoraggio
                    schedule.run_pending()
                    time.sleep(60)  # Controlla ogni minuto per scheduling preciso
                else:
                    # Fuori orario - calcola quando dormire
                    time_str = current_time.strftime("%H:%M")
                    
                    if current_time.time() < datetime.time(start_hour, 0):
                        # Prima delle 09:00 - aspetta fino alle 09:00
                        next_run = current_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
                        logging.info(f"⏸️  Prima dell'orario ({time_str}). Prossimo controllo alle {start_hour:02d}:00")
                    else:
                        # Dopo le 12:00 - aspetta fino alle 09:00 del giorno dopo
                        next_run = current_time.replace(hour=start_hour, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                        logging.info(f"⏸️  Fuori orario ({time_str}). Prossimo controllo domani alle {start_hour:02d}:00")
                    
                    # Calcola secondi da dormire (max 1 ora per controlli intermedi)
                    sleep_seconds = min((next_run - current_time).total_seconds(), 3600)
                    if sleep_seconds > 0:
                        time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                logging.info("🛑 Monitoraggio interrotto dall'utente")
                break
            except Exception as e:
                logging.error(f"❌ Errore nel loop di monitoraggio: {e}")
                time.sleep(300)  # Aspetta 5 minuti in caso di errore

    def _scheduled_check(self):
        """Esegue il controllo programmato solo se siamo nell'orario giusto"""
        if self.is_monitoring_time():
            current_time = datetime.datetime.now().strftime('%H:%M')
            logging.info(f"⏰ Controllo programmato: {current_time}")
            self.run_full_flow()
        else:
            current_time = datetime.datetime.now().strftime('%H:%M')
            logging.info(f"⏸️  Controllo saltato - fuori orario: {current_time}")

    def run_manual_flow(self, image_path: str):
        """Invia manualmente un'immagine via email"""
        logging.info(f"--- Flusso Manuale per: {image_path} ---")
        if not os.path.exists(image_path):
            logging.error(f"File non trovato: {image_path}")
            return
        self.notifier.send_menu_image(image_path, f"Immagine inviata manualmente - {datetime.date.today().strftime('%d/%m/%Y')}")

def main():
    setup_logging(CONFIG["LOG_FILE"])
    
    parser = argparse.ArgumentParser(description='Menu Extractor per Rosticceria Fantasia')
    parser.add_argument('--schedule', action='store_true', 
                       help='Esegui con monitoraggio programmato (09:00-12:00)')
    parser.add_argument('--manual', type=str, 
                       help='Invia immagine manualmente (percorso file)')
    parser.add_argument('--test', action='store_true',
                       help='Attiva modalità test (primo post con immagine)')
    
    args = parser.parse_args()
    
    # Attiva modalità test se richiesto
    if args.test:
        CONFIG["TEST_MODE"] = True
    
    extractor = MenuExtractor(CONFIG)
    
    if args.manual:
        # Modalità manuale
        extractor.run_manual_flow(args.manual)
    elif args.schedule:
        # Modalità con monitoraggio continuo
        extractor.run_scheduled_monitoring()
    else:
        # Modalità singola esecuzione (per GitHub Actions)
        extractor.run_full_flow()

if __name__ == "__main__":
    main()