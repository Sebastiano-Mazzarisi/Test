# ==============================================================================
#      SCRIPT FINALE: INVIO INTELLIGENTE DELL'IMMAGINE MENU VIA EMAIL
#
#                         -- VERSIONE 9.0 --
#
# OBIETTIVO: Eseguito ogni 15 minuti, cerca il menù e invia l'email solo
#            la prima volta che rileva un cambio rispetto al giorno precedente.
#            Dopodiché, si ferma per il resto della giornata.
# ==============================================================================

CONFIG = {
    "FACEBOOK_PAGE": "RosticceriaFantasia",
    "TARGET_KEYWORDS": ["MENU DEL GIORNO", "MENÙ DEL GIORNO", "IL NOSTRO MENU", "MENU DI OGGI"],
    "COOKIE_FILE": "cookies.txt", "OUTPUT_DIR": "output", "LOG_FILE": "output/menu_extractor.log",
    "STATUS_FILE": "status.json", # File per la "memoria" dello script
    "EMAIL_SENDER_ADDRESS": "s.mazzarisi@gmail.com",
    "EMAIL_SENDER_PASSWORD": "", # Letta dal Secret di GitHub
    "EMAIL_RECIPIENT_ADDRESS": "s.mazzarisi@mazzarisi.it",
    "EMAIL_SMTP_SERVER": "smtp.gmail.com", "EMAIL_SMTP_PORT": 587,
}

# ==============================================================================
# =================== FINE CONFIGURAZIONE - NON MODIFICARE SOTTO ===============
# ==============================================================================

import os, sys, datetime, logging, time, argparse, requests, html, json, hashlib
from typing import Dict, Optional, List
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"ERRORE: Manca una libreria -> {e.name}. Esegui 'pip install playwright requests Pillow' e 'playwright install'")
    sys.exit(1)

def setup_logging(log_path: str):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s",
                        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler(sys.stdout)])

class StateManager:
    """Gestisce la lettura e scrittura dello stato per evitare invii multipli."""
    def __init__(self, status_file):
        self.status_file = status_file
        self.state = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.status_file):
            return {}
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def has_sent_today(self) -> bool:
        today_str = datetime.date.today().isoformat()
        return self.state.get("last_sent_date") == today_str

    def is_new_menu(self, menu_text: str) -> bool:
        new_hash = hashlib.sha256(menu_text.encode('utf-8')).hexdigest()
        return self.state.get("last_menu_hash") != new_hash

    def update(self, menu_text: str):
        today_str = datetime.date.today().isoformat()
        new_hash = hashlib.sha256(menu_text.encode('utf-8')).hexdigest()
        self.state = {"last_sent_date": today_str, "last_menu_hash": new_hash}
        with open(self.status_file, 'w') as f:
            json.dump(self.state, f)
        logging.info(f"Stato aggiornato: email inviata per il menù del {today_str}.")

# ... Le altre classi (NotificationManager, FacebookScraper, etc.) rimangono quasi uguali ...
# (Le classi omesse sono state riportate per completezza nel blocco di codice finale)
class NotificationManager:
    def __init__(self, config: dict): self.config = config
    def send_menu_image(self, image_path: str, post_text: str = ""):
        sender, password, recipient = self.config.get("EMAIL_SENDER_ADDRESS"), self.config.get("EMAIL_SENDER_PASSWORD"), self.config.get("EMAIL_RECIPIENT_ADDRESS")
        if not all([sender, password, recipient]): return logging.error("Credenziali email non configurate."), False
        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = "Rosticceria Fantasia"
            msg['From'], msg['To'] = sender, recipient
            cleaned_text = html.escape(post_text)
            html_body = f"""<html><body style="font-family: sans-serif;"><pre style="font-family: sans-serif; font-size: 1em; white-space: pre-wrap; word-wrap: break-word;">{cleaned_text}</pre><img src="cid:menu_image"></body></html>"""
            msg.attach(MIMEText(html_body, 'html'))
            with open(image_path, 'rb') as f: img = MIMEImage(f.read()); img.add_header('Content-ID', '<menu_image>'); msg.attach(img)
            with smtplib.SMTP(self.config["EMAIL_SMTP_SERVER"], self.config["EMAIL_SMTP_PORT"]) as server:
                server.starttls(); server.login(sender, password); server.sendmail(sender, recipient, msg.as_string())
            logging.info("✅ Email inviata con successo!"); return True
        except Exception as e: logging.error(f"❌ Fallimento invio email: {e}"); return False
class FacebookScraper:
    def __init__(self, page_name: str, cookie_file_path: str): self.page_url = f"https://www.facebook.com/{page_name}"; self.cookie_file_path = cookie_file_path
    def _load_cookies_for_playwright(self) -> Optional[List[Dict]]:
        if not os.path.exists(self.cookie_file_path): logging.error(f"File cookie '{self.cookie_file_path}' non trovato."); return None
        cookies = []
        with open(self.cookie_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 7: cookies.append({'domain': parts[0], 'path': parts[2], 'secure': parts[3].upper() == 'TRUE', 'expires': int(parts[4]), 'name': parts[5], 'value': parts[6], 'httpOnly': False, 'sameSite': 'Lax'})
        if not any('.facebook.com' in c['domain'] for c in cookies): logging.error("Nessun cookie di Facebook trovato nel file."); return None
        logging.info(f"Caricati {len(cookies)} cookie validi."); return cookies
    def find_daily_menu_post(self, keywords: List[str]) -> Optional[Dict]:
        cookies = self._load_cookies_for_playwright()
        if not cookies: return None
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36')
                context.add_cookies(cookies); page = context.new_page()
                page.goto(self.page_url, wait_until='load', timeout=60000); time.sleep(5)
                posts = page.locator('div[aria-posinset]').all() or page.locator('div[role="article"]').all()
                for post_element in posts[:15]:
                    post_full_text = post_element.inner_text()
                    if any(keyword.upper() in post_full_text.upper() for keyword in keywords):
                        image_loc = post_element.locator('a[href*="photo"] img, img[data-visualcompletion="media-vc-image"]').first
                        if image_loc.is_visible(timeout=5000):
                            image_url = image_loc.get_attribute('src')
                            text_content_loc = post_element.locator('div[data-ad-preview="message"], div:has(> span[dir="auto"])').first
                            post_text_content = text_content_loc.inner_text() if text_content_loc.count() > 0 else ""
                            browser.close()
                            return {'image': image_url, 'text': post_text_content}
                browser.close(); return None
            except Exception as e:
                logging.error(f"Errore scraping Playwright: {e}")
                if browser and browser.is_connected(): browser.close()
                return None
class ImageProcessor:
    def __init__(self, output_dir: str): self.output_dir = output_dir; os.makedirs(output_dir, exist_ok=True)
    def download_image(self, post_data: Dict) -> Optional[str]:
        image_url = post_data.get("image")
        if not image_url: return logging.error("URL immagine non trovato."), None
        try:
            response = requests.get(image_url, timeout=30); response.raise_for_status()
            filepath = os.path.join(self.output_dir, f"menu_{datetime.date.today().strftime('%Y%m%d')}.jpg")
            with open(filepath, 'wb') as f: f.write(response.content)
            logging.info(f"Immagine scaricata: {filepath}"); return filepath
        except requests.RequestException as e: return logging.error(f"Errore download: {e}"), None

class MenuExtractor:
    def __init__(self, config: dict):
        config["EMAIL_SENDER_PASSWORD"] = os.getenv('GMAIL_APP_PASSWORD', config.get("EMAIL_SENDER_PASSWORD"))
        self.config = config
        self.scraper = FacebookScraper(config["FACEBOOK_PAGE"], config["COOKIE_FILE"])
        self.processor = ImageProcessor(config["OUTPUT_DIR"])
        self.notifier = NotificationManager(config)
        self.state_manager = StateManager(config["STATUS_FILE"])

    def run_full_flow(self):
        logging.info("--- Inizio Flusso di Controllo Menù ---")

        if self.state_manager.has_sent_today():
            logging.info("Email per il menù di oggi già inviata. Termino l'esecuzione.")
            return

        post = self.scraper.find_daily_menu_post(self.config["TARGET_KEYWORDS"])
        if not post: return logging.info("Nessun post del menù trovato al momento.")
        
        post_text = post.get("text", "")
        if not self.state_manager.is_new_menu(post_text):
            logging.info("Trovato menù, ma è lo stesso del giorno precedente. Attendo aggiornamento.")
            return

        logging.info("Trovato un NUOVO menù! Procedo con download e invio email...")
        image_path = self.processor.download_image(post)
        if not image_path: return logging.error("Download fallito.")
        
        if self.notifier.send_menu_image(image_path, post_text):
            self.state_manager.update(post_text)
        
        logging.info("--- Flusso Completato con Successo ---")

def main():
    setup_logging(CONFIG["LOG_FILE"])
    extractor = MenuExtractor(CONFIG)
    extractor.run_full_flow()

if __name__ == "__main__":
    main()