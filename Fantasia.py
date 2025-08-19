# ==============================================================================
#      SCRIPT FINALE PER GITHUB ACTIONS
#
#                         -- VERSIONE 16.0 --
#
# OBIETTIVO: Essere eseguito in modo automatico su GitHub Actions.
#            Estrae i dati da Facebook, li salva in un file HTML e invia un'email.
# ==============================================================================

CONFIG = {
    # Configurazione Scraping
    "FACEBOOK_PAGE": "RosticceriaFantasia",
    "TARGET_KEYWORDS": ["MENU DEL GIORNO", "MENÙ DEL GIORNO", "IL NOSTRO MENU", "MENU DI OGGI"],
    "COOKIE_FILE": "cookies.txt",
    "OUTPUT_DIR": ".",
    "LOG_FILE": "menu_extractor.log",

    # Configurazione Email (La password viene letta dal Secret di GitHub)
    "EMAIL_SENDER_ADDRESS": "s.mazzarisi@gmail.com",
    "EMAIL_RECIPIENT_ADDRESS": "s.mazzarisi@mazzarisi.it",
    "EMAIL_SMTP_SERVER": "smtp.gmail.com",
    "EMAIL_SMTP_PORT": 587,
}

# ==============================================================================
# =================== FINE CONFIGURAZIONE - NON MODIFICARE SOTTO ===============
# ==============================================================================

import os
import sys
import datetime
import logging
import time
import requests
import html
import pytz
from typing import Dict, Optional, List

# Import per le email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError as e:
    print(f"ERRORE: Manca una libreria fondamentale -> {e.name}.")
    print("Esegui 'pip install playwright requests' e poi 'playwright install'")
    sys.exit(1)

def setup_logging(log_path: str):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s",
                        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler(sys.stdout)])

class NotificationManager:
    def __init__(self, config: dict):
        self.config = config

    def send_menu_image(self, image_path: str, post_text: str = ""):
        sender, password, recipient = self.config.get("EMAIL_SENDER_ADDRESS"), self.config.get("EMAIL_SENDER_PASSWORD"), self.config.get("EMAIL_RECIPIENT_ADDRESS")
        if not all([sender, password, recipient]):
            logging.error("Credenziali email non configurate o password mancante.")
            return False
        
        logging.info(f"Preparo l'email HTML pulita per {recipient}...")
        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = "Rosticceria Fantasia"
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
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, recipient, msg.as_string())
            logging.info("✅ Email inviata con successo!")
            return True
        except Exception as e:
            logging.error(f"❌ Fallimento invio email: {e}")
            return False

class FacebookScraper:
    def __init__(self, page_name: str, cookie_file_path: str):
        self.page_url = f"https://www.facebook.com/{page_name}"
        self.cookie_file_path = cookie_file_path
        
    def _load_cookies_for_playwright(self) -> Optional[List[Dict]]:
        if not os.path.exists(self.cookie_file_path):
            logging.error(f"File cookie '{self.cookie_file_path}' non trovato.")
            return None
        
        cookies = []
        with open(self.cookie_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 7:
                    try:
                        cookies.append({
                            'domain': parts[0],
                            'path': parts[2],
                            'secure': parts[3].upper() == 'TRUE',
                            'expires': int(parts[4]),
                            'name': parts[5],
                            'value': parts[6],
                            'httpOnly': False,
                            'sameSite': 'Lax'
                        })
                    except ValueError:
                        logging.error(f"Riga del cookie malformata: {line.strip()}")
        if not any('.facebook.com' in c['domain'] for c in cookies):
            logging.error("Nessun cookie di Facebook valido trovato nel file.")
            return None
        
        logging.info(f"Caricati {len(cookies)} cookie validi.")
        return cookies

    def find_daily_menu_post(self, keywords: List[str]) -> Optional[Dict]:
        logging.info(f"Avvio scraping con Playwright per '{self.page_url}'...")
        cookies = self._load_cookies_for_playwright()
        if not cookies:
            return None
            
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
                )
                context.add_cookies(cookies)
                page = context.new_page()
                page.goto(self.page_url, wait_until='load', timeout=60000)
                time.sleep(5)
                
                posts = page.locator('div[aria-posinset]').all() or page.locator('div[role="article"]').all()
                logging.info(f"Trovati {len(posts)} post candidati.")
                
                for post_element in posts[:15]:
                    post_full_text = post_element.inner_text()
                    keywords_match = any(keyword.upper() in post_full_text.upper() for keyword in keywords)
                    
                    if keywords_match:
                        image_loc = post_element.locator('a[href*="photo"] img, img[data-visualcompletion="media-vc-image"]').first
                        if image_loc.is_visible(timeout=5000):
                            image_url = image_loc.get_attribute('src')
                            text_content_loc = post_element.locator('div[data-ad-preview="message"], div:has(> span[dir="auto"])').first
                            post_text_content = text_content_loc.inner_text() if text_content_loc.count() > 0 else ""
                            
                            logging.info("🎉 Post del menù trovato!")
                            browser.close()
                            return {'image': image_url, 'text': post_text_content}
                
                browser.close()
                return None
            except Exception as e:
                logging.error(f"Errore scraping Playwright: {e}")
                if browser and browser.is_connected():
                    browser.close()
                return None

class ImageProcessor:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def download_image(self, post_data: Dict) -> Optional[str]:
        image_url = post_data.get("image")
        if not image_url:
            logging.error("URL immagine non trovato.")
            return None
            
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            filepath = os.path.join(self.output_dir, f"menu_{datetime.date.today().strftime('%Y%m%d')}.jpg")
            with open(filepath, 'wb') as f:
                f.write(response.content)
            logging.info(f"Immagine scaricata: {filepath}")
            return filepath
        except requests.RequestException as e:
            logging.error(f"Errore download: {e}")
            return None

class MenuExtractor:
    def __init__(self, config: dict):
        config["EMAIL_SENDER_PASSWORD"] = os.getenv('GMAIL_APP_PASSWORD', config.get("EMAIL_SENDER_PASSWORD"))
        self.config = config
        self.scraper = FacebookScraper(config["FACEBOOK_PAGE"], config["COOKIE_FILE"])
        self.processor = ImageProcessor(config["OUTPUT_DIR"])
        self.notifier = NotificationManager(config)

    def run_full_flow(self):
        logging.info("--- Inizio Flusso Estrazione Menu ---")
        post = self.scraper.find_daily_menu_post(self.config["TARGET_KEYWORDS"])
        if not post:
            logging.error("Processo interrotto: post non trovato.")
            return
        image_path = self.processor.download_image(post)
        if not image_path:
            logging.error("Processo interrotto: download fallito.")
            return
        self.notifier.send_menu_image(image_path, post.get("text", ""))
        logging.info("--- Flusso Completato con Successo ---")

def main():
    setup_logging(CONFIG["LOG_FILE"])
    extractor = MenuExtractor(CONFIG)
    extractor.run_full_flow()

if __name__ == "__main__":
    main()