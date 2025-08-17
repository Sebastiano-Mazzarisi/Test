import os
import requests
from bs4 import BeautifulSoup
from github import Github

# --- Configurazione GitHub ---
# La variabile d'ambiente GITHUB_TOKEN verrà fornita automaticamente da GitHub Actions.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "Sebastiano-Mazzarisi"
REPO_NAME = "Test"
FILE_PATH = "Monitorizza.html"
# --- ---

def get_zip_files(url):
    """Recupera e analizza la pagina web per trovare tutti i file .zip."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        links = soup.find_all('a', href=lambda href: href and href.endswith('.zip'))
        
        zip_files = []
        for link in links:
            file_name = os.path.basename(link['href'])
            mod_date = "Data sconosciuta" 
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
    html_content += "<h1>Elenco file .zip aggiornato</h1>\n"
    html_content += "<ul>\n"
    
    for date, name in file_list:
        html_content += f"    <li><b>{date}</b> --- {name}</li>\n"
    
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
        except Exception:
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
        print("Errore: la variabile d'ambiente GITHUB_TOKEN non è impostata. Questo è normale se lo script è eseguito al di fuori di GitHub Actions.")
    else:
        URL_TO_SCRAPE = "https://www.pugliausr.gov.it/"
        
        print("Avvio del processo di monitoraggio...")
        zip_files = get_zip_files(URL_TO_SCRAPE)
        
        if zip_files is not None:
            zip_files.sort(key=lambda x: x[1], reverse=True)
            html_output = create_html_content(zip_files)
            commit_msg = "Aggiornamento automatico elenco file .zip"
            update_github_file(REPO_OWNER, REPO_NAME, FILE_PATH, html_output, commit_msg)