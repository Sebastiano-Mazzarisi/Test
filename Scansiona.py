import os
from github import Github
from datetime import datetime
import pytz

# --- Configurazione GitHub ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "Sebastiano-Mazzarisi"
REPO_NAME = "Test"
FILE_PATH = "Monitorizza.html"
# --- ---

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
        print("Errore: la variabile d'ambiente GITHUB_TOKEN non è impostata.")
    else:
        # Crea il contenuto HTML con data e ora
        timezone = pytz.timezone('Europe/Rome')
        now = datetime.now(timezone)
        html_content = f"<html><body><p>Test eseguito il: {now.strftime('%Y-%m-%d alle %H:%M:%S')}</p></body></html>"
        
        commit_msg = "Test automatico del workflow"
        
        # Aggiorna il file su GitHub
        update_github_file(REPO_OWNER, REPO_NAME, FILE_PATH, html_content, commit_msg)