# ==============================================================================
#    SCRIPT PER INVIARE L'ULTIMA IMMAGINE PUBBLICATA (ANCHE SENZA "MENU")
#
#                         -- VERSIONE 9.4 ULTIMA IMMAGINE --
# ==============================================================================

CONFIG = {
    # Configurazione Scraping
    "FACEBOOK_PAGE": "RosticceriaFantasia",
    "COOKIE_FILE": "cookies.txt",
    "OUTPUT_DIR": "output",
    "LOG_FILE": "output/menu_extractor.log",

    # Configurazione Email
    "EMAIL_SENDER_ADDRESS": "s.mazzarisi@gmail.com",
    "EMAIL_SENDER_PASSWORD": "",
    "EMAIL_RECIPIENT_ADDRESS": "s.mazzarisi@mazzarisi.it",
    "EMAIL_SMTP_SERVER": "smtp.gmail.com",
    "EMAIL_SMTP_PORT": 587,
    
    # MODALITÀ: 
    # "MENU" = cerca solo post con parola MENU
    # "LATEST" = invia l'ultima immagine pubblicata
    # "TEST" = invia la prima immagine che trova
    "SEARCH_MODE": "LATEST",
}

import os
import sys
import datetime
import logging
import time
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
            mode_suffix = f" [{self.config.get('SEARCH_MODE', 'UNKNOWN')} MODE]"
            msg['Subject'] = f"Rosticceria Fantasia{mode_suffix}"
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
    
    def find_post_by_mode(self, search_mode: str) -> Optional[Dict]:
        logging.info(f"🚀 Avvio scraping in modalità: {search_mode}")
        
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
                
                # Attendi e scrolla
                logging.info("⏳ Caricamento pagina e scroll...")
                time.sleep(10)
                for i in range(6):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(3)
                
                # STRATEGIA NUOVA: Cerca direttamente tutte le immagini di contenuto
                logging.info("🔍 Strategia diretta: cercando TUTTE le immagini sulla pagina...")
                all_images = page.locator('img').all()
                logging.info(f"📸 Trovate {len(all_images)} immagini totali")
                
                # Filtra solo le immagini di contenuto vere
                content_images = []
                for i, img in enumerate(all_images):
                    try:
                        src = img.get_attribute('src')
                        if src and ('scontent' in src or 'fbcdn' in src) and len(src) > 50:
                            # Controlla se è un'immagine grande (probabilmente un post)
                            try:
                                # Ottieni dimensioni se possibile
                                width = img.get_attribute('width')
                                height = img.get_attribute('height')
                                
                                # Se ha dimensioni decenti o se il src sembra essere un post
                                is_content_image = (
                                    'scontent' in src and 
                                    ('_n.' in src or '_o.' in src or len(src) > 100)  # URL lunghi sono spesso immagini di post
                                )
                                
                                if is_content_image:
                                    content_images.append((img, src))
                                    logging.info(f"✅ Immagine #{len(content_images)}: {src[:70]}...")
                                    
                            except:
                                # Se non riusciamo a ottenere info, accettiamo comunque se ha scontent
                                if 'scontent' in src:
                                    content_images.append((img, src))
                                    logging.info(f"✅ Immagine #{len(content_images)} (fallback): {src[:70]}...")
                                    
                    except Exception as e:
                        logging.debug(f"Errore immagine #{i}: {e}")
                        continue
                
                logging.info(f"🖼️ Trovate {len(content_images)} immagini di contenuto")
                
                if not content_images:
                    logging.error("❌ Nessuna immagine di contenuto trovata!")
                    browser.close()
                    return None
                
                # Analizza ogni immagine di contenuto per trovare il testo associato
                for i, (img_element, img_src) in enumerate(content_images):
                    try:
                        logging.info(f"━━━ ANALIZZANDO IMMAGINE #{i+1}/{len(content_images)} ━━━")
                        logging.info(f"🖼️ URL: {img_src[:60]}...")
                        
                        # Trova il contenitore del post risalendo nella gerarchia
                        post_text = ""
                        
                        # Prova diversi metodi per trovare il testo associato
                        try:
                            # Metodo 1: Cerca il div padre che contiene testo
                            parent_levels = [2, 3, 4, 5, 6, 7, 8]
                            for level in parent_levels:
                                try:
                                    parent = img_element.locator(f'xpath=ancestor::div[{level}]').first
                                    if parent.count() > 0:
                                        parent_text = parent.inner_text()
                                        if len(parent_text) > 20:  # Solo se ha abbastanza testo
                                            post_text = parent_text
                                            logging.info(f"📝 Testo trovato al livello {level} (primi 200 char): {parent_text[:200]}")
                                            break
                                except:
                                    continue
                        except:
                            pass
                        
                        # Se non troviamo testo, prova un approccio diverso
                        if not post_text:
                            try:
                                # Metodo 2: Cerca elementi di testo vicini all'immagine
                                nearby_text_elements = page.locator('span, p, div').all()
                                for elem in nearby_text_elements[:50]:  # Limita per performance
                                    try:
                                        elem_text = elem.inner_text()
                                        if len(elem_text) > 10 and ('menu' in elem_text.lower() or 'del giorno' in elem_text.lower()):
                                            post_text = elem_text
                                            logging.info(f"📝 Testo trovato tramite ricerca nearby: {elem_text[:200]}")
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        
                        # Se ancora non abbiamo testo, usa un placeholder
                        if not post_text:
                            post_text = f"Immagine #{i+1} dalla pagina Rosticceria Fantasia - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
                            logging.info("📝 Usando testo placeholder")
                        
                        # Controlla in base alla modalità
                        if search_mode == "TEST":
                            logging.info(f"🧪 TEST MODE: Accetto immagine #{i+1}")
                            browser.close()
                            return {'image': img_src, 'text': f"[MODALITÀ TEST]\n\n{post_text}"}
                        
                        elif search_mode == "LATEST":
                            logging.info(f"📅 LATEST MODE: Accetto prima immagine trovata #{i+1}")
                            browser.close()
                            return {'image': img_src, 'text': f"[ULTIMA IMMAGINE PUBBLICATA]\n\n{post_text}"}
                        
                        elif search_mode == "MENU":
                            # Cerca specificatamente "MENU" nel testo
                            if "MENU" in post_text.upper() or "MENÙ" in post_text.upper():
                                logging.info(f"🎯 MENU MODE: TROVATO! Immagine #{i+1} contiene MENU!")
                                browser.close()
                                return {'image': img_src, 'text': post_text}
                            else:
                                logging.info(f"⚠️ Immagine #{i+1}: Non contiene MENU, continuo...")
                                # Continua con la prossima immagine
                                continue
                        
                    except Exception as e:
                        logging.warning(f"Errore analisi immagine #{i+1}: {e}")
                        continue
                
                # Se arriviamo qui, non abbiamo trovato nulla
                if search_mode == "MENU":
                    logging.error("❌ Nessuna immagine con MENU trovata")
                else:
                    logging.error("❌ Nessuna immagine elaborabile trovata")
                
                browser.close()
                return None
                
            except Exception as e:
                logging.error(f"Errore scraping: {e}")
                if browser and browser.is_connected(): 
                    browser.close()
                return None
    
    # Rimuovi i metodi vecchi che non servono più
    # Ora tutto è gestito nel metodo principale find_post_by_mode

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
        config["EMAIL_SENDER_PASSWORD"] = os.getenv('GMAIL_APP_PASSWORD', config.get("EMAIL_SENDER_PASSWORD"))
        
        # Modalità da variabile d'ambiente o config
        search_mode = os.getenv('SEARCH_MODE', config.get("SEARCH_MODE", "LATEST"))
        config["SEARCH_MODE"] = search_mode
        
        self.config = config
        self.scraper = FacebookScraper(config["FACEBOOK_PAGE"], config["COOKIE_FILE"])
        self.processor = ImageProcessor(config["OUTPUT_DIR"])
        self.notifier = NotificationManager(config)

    def run_full_flow(self):
        search_mode = self.config.get("SEARCH_MODE", "LATEST")
        
        logging.info(f"--- Inizio Flusso in modalità: {search_mode} ---")
        
        post = self.scraper.find_post_by_mode(search_mode)
        if not post: 
            return logging.error("Processo interrotto: post non trovato.")
        
        image_path = self.processor.download_image(post)
        if not image_path: 
            return logging.error("Processo interrotto: download fallito.")
        
        self.notifier.send_menu_image(image_path, post.get("text", ""))
        logging.info("--- Flusso Completato con Successo ---")

def main():
    setup_logging(CONFIG["LOG_FILE"])
    extractor = MenuExtractor(CONFIG)
    extractor.run_full_flow()

if __name__ == "__main__":
    main()