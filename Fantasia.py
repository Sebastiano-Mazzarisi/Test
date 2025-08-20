# ==============================================================================
#      SCRIPT FINALE PER GITHUB ACTIONS
#
#                         -- VERSIONE 17.0 --
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
    "HTML_OUTPUT": "Fantasia.html",

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
    """Configura il sistema di logging"""
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'), 
            logging.StreamHandler(sys.stdout)
        ]
    )

class HTMLGenerator:
    """Classe per generare file HTML con il menù"""
    
    def __init__(self, output_dir: str, html_filename: str):
        self.output_dir = output_dir
        self.html_filename = html_filename
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_file(self, image_path: str, post_text: str = ""):
        """Genera il file HTML con immagine e testo del menù"""
        html_path = os.path.join(self.output_dir, self.html_filename)
        
        # Ottieni solo il nome del file immagine (senza path)
        image_filename = os.path.basename(image_path) if image_path else ""
        
        # Pulisci il testo per HTML
        cleaned_text = html.escape(post_text) if post_text else ""
        
        # Template HTML
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rosticceria Fantasia</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #d2691e;
            text-align: center;
            margin-bottom: 20px;
        }}
        .menu-text {{
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 20px;
            white-space: pre-wrap;
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
        }}
        .menu-image {{
            text-align: center;
            margin: 20px 0;
        }}
        .menu-image img {{
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .timestamp {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 20px;
            border-top: 1px solid #eee;
            padding-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🍽️ Rosticceria Fantasia</h1>
        
        {f'<div class="menu-text">{cleaned_text}</div>' if cleaned_text else ''}
        
        {f'<div class="menu-image"><img src="{image_filename}" alt="Menù del giorno" /></div>' if image_filename else ''}
        
        <div class="timestamp">
            Ultimo aggiornamento: {datetime.datetime.now(pytz.timezone('Europe/Rome')).strftime('%d/%m/%Y alle %H:%M')}
        </div>
    </div>
</body>
</html>"""
        
        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logging.info(f"✅ File HTML generato: {html_path}")
            return html_path
        except Exception as e:
            logging.error(f"❌ Errore nella generazione HTML: {e}")
            return None

class NotificationManager:
    """Classe per gestire le notifiche email"""
    
    def __init__(self, config: dict):
        self.config = config

    def send_menu_email(self, image_path: str, post_text: str = ""):
        """Invia email con il menù"""
        sender = self.config.get("EMAIL_SENDER_ADDRESS")
        password = self.config.get("EMAIL_SENDER_PASSWORD")
        recipient = self.config.get("EMAIL_RECIPIENT_ADDRESS")
        
        if not all([sender, password, recipient]):
            logging.error("❌ Credenziali email non configurate o password mancante.")
            return False
        
        logging.info(f"📧 Preparo l'email per {recipient}...")
        
        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = "🍽️ Rosticceria Fantasia - Menù del Giorno"
            msg['From'] = sender
            msg['To'] = recipient
            
            # Pulisci il testo per HTML
            cleaned_text = html.escape(post_text) if post_text else "Nessun testo disponibile"
            
            html_body = f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <h2 style="color: #d2691e;">🍽️ Rosticceria Fantasia - Menù del Giorno</h2>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <pre style="font-family: Arial, sans-serif; font-size: 14px; white-space: pre-wrap; word-wrap: break-word; margin: 0;">{cleaned_text}</pre>
                </div>
                <div style="text-align: center; margin: 20px 0;">
                    <img src="cid:menu_image" style="max-width: 100%; height: auto; border-radius: 10px;">
                </div>
                <hr>
                <p style="color: #666; font-size: 12px; text-align: center;">
                    Aggiornamento automatico del {datetime.datetime.now(pytz.timezone('Europe/Rome')).strftime('%d/%m/%Y alle %H:%M')}
                </p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Allega l'immagine se disponibile
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    img = MIMEImage(f.read())
                img.add_header('Content-ID', '<menu_image>')
                msg.attach(img)
            
            # Invia l'email
            logging.info(f"📤 Invio email a {recipient}...")
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
    """Classe per lo scraping di Facebook"""
    
    def __init__(self, page_name: str, cookie_file_path: str):
        self.page_url = f"https://www.facebook.com/{page_name}"
        self.cookie_file_path = cookie_file_path
        
    def _load_cookies_for_playwright(self) -> Optional[List[Dict]]:
        """Carica i cookie dal file per Playwright"""
        if not os.path.exists(self.cookie_file_path):
            logging.error(f"❌ File cookie '{self.cookie_file_path}' non trovato.")
            return None
        
        cookies = []
        with open(self.cookie_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Salta righe vuote e commenti
                if not line or line.startswith('#') or 'Netscape' in line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 7:
                    try:
                        cookies.append({
                            'domain': parts[0],
                            'path': parts[2],
                            'secure': parts[3].upper() == 'TRUE',
                            'expires': int(parts[4]) if parts[4] != '0' else -1,
                            'name': parts[5],
                            'value': parts[6],
                            'httpOnly': False,
                            'sameSite': 'Lax'
                        })
                    except (ValueError, IndexError) as e:
                        logging.warning(f"⚠️ Riga {line_num} del cookie malformata: {line} - {e}")
                        continue
        
        if not cookies:
            logging.error("❌ Nessun cookie valido trovato nel file.")
            return None
            
        facebook_cookies = [c for c in cookies if '.facebook.com' in c['domain']]
        if not facebook_cookies:
            logging.error("❌ Nessun cookie di Facebook valido trovato nel file.")
            return None
        
        logging.info(f"✅ Caricati {len(cookies)} cookie totali ({len(facebook_cookies)} per Facebook).")
        return cookies

    def find_daily_menu_post(self, keywords: List[str]) -> Optional[Dict]:
        """Trova il post del menù del giorno su Facebook"""
        logging.info(f"🔍 Avvio scraping con Playwright per '{self.page_url}'...")
        
        cookies = self._load_cookies_for_playwright()
        if not cookies:
            return None
            
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                context.add_cookies(cookies)
                page = context.new_page()
                
                logging.info("🌐 Caricamento pagina Facebook...")
                page.goto(self.page_url, wait_until='load', timeout=60000)
                time.sleep(8)  # Attesa per il caricamento dinamico
                
                # Cerca i post
                post_selectors = [
                    'div[aria-posinset]',
                    'div[role="article"]',
                    'div[data-pagelet="FeedUnit_0"]',
                    'div[data-ft]'
                ]
                
                posts = []
                for selector in post_selectors:
                    try:
                        elements = page.locator(selector).all()
                        if elements:
                            posts = elements
                            logging.info(f"✅ Trovati {len(posts)} post con selettore: {selector}")
                            break
                    except Exception as e:
                        logging.warning(f"⚠️ Selettore {selector} non funzionante: {e}")
                        continue
                
                if not posts:
                    logging.error("❌ Nessun post trovato con tutti i selettori.")
                    return None
                
                # Analizza i post
                for i, post_element in enumerate(posts[:20]):  # Controlla i primi 20 post
                    try:
                        post_full_text = post_element.inner_text()
                        
                        # Controlla se contiene le keyword del menù
                        keywords_match = any(keyword.upper() in post_full_text.upper() for keyword in keywords)
                        
                        if keywords_match:
                            logging.info(f"🎯 Post #{i+1} contiene keyword del menù!")
                            
                            # Cerca l'immagine
                            image_selectors = [
                                'a[href*="photo"] img',
                                'img[data-visualcompletion="media-vc-image"]',
                                'img[src*="scontent"]',
                                'div[data-attachment-type="photo"] img'
                            ]
                            
                            image_url = None
                            for img_selector in image_selectors:
                                try:
                                    image_loc = post_element.locator(img_selector).first
                                    if image_loc.is_visible(timeout=3000):
                                        image_url = image_loc.get_attribute('src')
                                        if image_url:
                                            logging.info(f"📸 Immagine trovata con selettore: {img_selector}")
                                            break
                                except Exception as e:
                                    continue
                            
                            if not image_url:
                                logging.warning(f"⚠️ Post #{i+1} ha keyword ma nessuna immagine trovata.")
                                continue
                            
                            # Estrai il testo del post
                            text_selectors = [
                                'div[data-ad-preview="message"]',
                                'div[dir="auto"]',
                                'span[dir="auto"]'
                            ]
                            
                            post_text_content = ""
                            for text_selector in text_selectors:
                                try:
                                    text_elements = post_element.locator(text_selector).all()
                                    if text_elements:
                                        post_text_content = "\n".join([elem.inner_text() for elem in text_elements[:3]])
                                        if post_text_content.strip():
                                            break
                                except Exception as e:
                                    continue
                            
                            logging.info("🎉 Post del menù trovato con successo!")
                            return {
                                'image': image_url,
                                'text': post_text_content.strip()
                            }
                    
                    except Exception as e:
                        logging.warning(f"⚠️ Errore nell'analisi del post #{i+1}: {e}")
                        continue
                
                logging.error("❌ Nessun post del menù trovato nei primi 20 post.")
                return None
                
            except Exception as e:
                logging.error(f"❌ Errore scraping Playwright: {e}")
                return None
            finally:
                if browser and browser.is_connected():
                    browser.close()

class ImageProcessor:
    """Classe per il processing delle immagini"""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def download_image(self, post_data: Dict) -> Optional[str]:
        """Scarica l'immagine del menù"""
        image_url = post_data.get("image")
        if not image_url:
            logging.error("❌ URL immagine non trovato nei dati del post.")
            return None
            
        try:
            logging.info("⬇️ Download immagine in corso...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
            }
            
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Nome file con timestamp
            today = datetime.date.today().strftime('%Y%m%d')
            filepath = os.path.join(self.output_dir, f"menu_{today}.jpg")
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"✅ Immagine scaricata: {filepath} ({len(response.content)} bytes)")
            return filepath
            
        except requests.RequestException as e:
            logging.error(f"❌ Errore download immagine: {e}")
            return None

class MenuExtractor:
    """Classe principale per l'estrazione del menù"""
    
    def __init__(self, config: dict):
        # Leggi la password email dai secrets di GitHub Actions
        config["EMAIL_SENDER_PASSWORD"] = os.getenv('GMAIL_APP_PASSWORD', config.get("EMAIL_SENDER_PASSWORD"))
        
        self.config = config
        self.scraper = FacebookScraper(config["FACEBOOK_PAGE"], config["COOKIE_FILE"])
        self.processor = ImageProcessor(config["OUTPUT_DIR"])
        self.notifier = NotificationManager(config)
        self.html_generator = HTMLGenerator(config["OUTPUT_DIR"], config["HTML_OUTPUT"])

    def run_full_flow(self):
        """Esegue l'intero flusso di estrazione del menù"""
        logging.info("🚀 --- Inizio Flusso Estrazione Menu ---")
        
        # Passo 1: Trova il post del menù
        post = self.scraper.find_daily_menu_post(self.config["TARGET_KEYWORDS"])
        if not post:
            logging.error("❌ Processo interrotto: post del menù non trovato.")
            return False
        
        # Passo 2: Scarica l'immagine
        image_path = self.processor.download_image(post)
        if not image_path:
            logging.error("❌ Processo interrotto: download immagine fallito.")
            return False
        
        # Passo 3: Genera il file HTML
        html_path = self.html_generator.generate_html_file(image_path, post.get("text", ""))
        if not html_path:
            logging.error("❌ Processo interrotto: generazione HTML fallita.")
            return False
        
        # Passo 4: Invia email (opzionale)
        email_sent = self.notifier.send_menu_email(image_path, post.get("text", ""))
        if email_sent:
            logging.info("✅ Email inviata con successo!")
        else:
            logging.warning("⚠️ Email non inviata, ma il processo continua.")
        
        logging.info("🎉 --- Flusso Completato con Successo ---")
        return True

def main():
    """Funzione principale"""
    # Setup logging
    setup_logging(CONFIG["LOG_FILE"])
    
    logging.info("=" * 60)
    logging.info("🍽️ ROSTICCERIA FANTASIA - MENU EXTRACTOR v17.0")
    logging.info("=" * 60)
    
    # Controllo file necessari
    if not os.path.exists(CONFIG["COOKIE_FILE"]):
        logging.error(f"❌ File cookie '{CONFIG['COOKIE_FILE']}' non trovato!")
        logging.error("   Assicurati che il file cookies.txt sia presente nella root del repository.")
        sys.exit(1)
    
    # Avvia l'estrazione
    extractor = MenuExtractor(CONFIG)
    success = extractor.run_full_flow()
    
    if success:
        logging.info("🎉 Estrazione completata con successo!")
        sys.exit(0)
    else:
        logging.error("❌ Estrazione fallita!")
        sys.exit(1)

if __name__ == "__main__":
    main()