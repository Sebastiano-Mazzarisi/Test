import os
import requests
from bs4 import BeautifulSoup
from github import Github
from datetime import datetime
import pytz

# --- Configurazione GitHub ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "Sebastiano-Mazzarisi"
REPO_NAME = "Test"
FILE_PATH = "Monitorizza.html"
# --- ---

def get_zip_files(url):
    """
    Recupera e analizza la pagina web per trovare tutti i file .zip e la loro data.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Trova tutti i blocchi di notizie che contengono i link.
        news_items = soup.find_all('div', class_='news_list-item')
        
        zip_files = []
        for item in news_items:
            # All'interno di ogni blocco, cerca il tag della data
            date_tag = item.find('span', class_='news-date')
            
            # E cerca il link al file .zip
            link = item.find('a', href=lambda href: href and href.endswith('.zip'))
            
            # Se entrambi vengono trovati, estrai le informazioni
            if date_tag and link:
                file_name = os.path.basename(link['href'])
                date_str = date_tag.text.strip()
                
                # Estrae la data dalla stringa (es. "Pubblicato: Sabato, 16 Agosto 2025 18:00")
                try:
                    parts = date_str.split(',')
                    date_part = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                    mod_date = datetime.strptime(date_part, '%d %B %Y') 
                except (ValueError, IndexError):
                    mod_date = datetime(1900, 1, 1)
                
                zip_files.append((mod_date, file_name))
            
        return zip_files
    
    except requests.exceptions.RequestException as e:
        print(f"Errore durante la richiesta HTTP: {e}")
        return None

def create_html_content(file_list):
    """Genera il contenuto HTML per il file Monitorizza.html."""
    if not file_list:
        return "<html><body><p>Nessun file .zip trovato.</p></body></html>"

    html_content = "<html>\n<head><title>Monitoraggio File .zip</title></head>\n<body>\n"
    html_content += f"<h1>Elenco file .zip aggiornato ({len(file_list)} file trovati)</h1>\n"
    html_content += "<ul>\n"
    
    for date, name in file_list:
        date_str = date.strftime('%Y-%m-%d') if date.year > 1900 else "Data non trovata"
        html_content += f"    <li><b>{date_str}</b> --- {name}</li>\n"
    
    html_content += "</ul>\n</body>\n</html>"
    return html_content

def update_github_file(repo_owner, repo_name, file_path, new_content, commit_message):
    """Si connette a GitHub e aggiorna un file nel repository."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_user(repo_owner).get_repo(repo_name)
        
        try:
            file_to_update = repo.get_contents(file_path)
            repo.update_file(
                path=file_to_update.path,
                message=commit_message,
                content=new_content,
                sha=file_to_update.sha,
                branch="main"
            )
            print(f"File '{file_path}' aggiornato con successo su GitHub.")
        except Exception as e:
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=new_content,
                branch="main"
            )
            print(f"File '{file_path}' creato con successo su GitHub.")

    except Exception as e:
        print(f"Errore durante l'aggiornamento del file su GitHub: {e}")

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("Errore: la variabile d'ambiente GITHUB_TOKEN non è impostata.")
    else:
        URL_TO_SCRAPE = "https://www.pugliausr.gov.it/"
        
        print("Avvio del processo di monitoraggio...")
        zip_files = get_zip_files(URL_TO_SCRAPE)
        
        if zip_files is not None:
            zip_files.sort(key=lambda x: x[0])
            
            if len(zip_files) > 15:
                zip_files = zip_files[:15]
            
            html_output = create_html_content(zip_files)
            commit_msg = "Aggiornamento automatico elenco file .zip"
            update_github_file(REPO_OWNER, REPO_NAME, FILE_PATH, html_output, commit_msg)