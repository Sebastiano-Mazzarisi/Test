import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import zipfile
import tempfile
import shutil
import re
from PyPDF2 import PdfReader
import logging
from urllib.parse import urljoin
from github import Github

# Configurazione per sopprimere gli avvisi di PyPDF2
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

# --- Configurazione Globale ---
FILE_PATH = "Monitorizza.html"
SEARCH_STRINGS = ["Mazzarisi", "Ximenes", "Occhiuto", "A045"]
ROOT_URL = "https://www.pugliausr.gov.it/"
# --- ---

def _parse_italian_datetime_from_text(text: str):
    MONTHS_IT = {
        "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
        "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
        "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
        "màggio": 5, "agòsto": 8, "òttobre": 10, "décembre": 12
    }
    RE_PUBBLICATO = re.compile(
        r"Pubblicato:\s*\w+,\s*(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?",
        re.IGNORECASE
    )
    RE_PUBBLICATO_NO_WD = re.compile(
        r"Pubblicato:\s*(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?",
        re.IGNORECASE
    )

    if not text:
        return None
    m = RE_PUBBLICATO.search(text)
    if not m:
        m = RE_PUBBLICATO_NO_WD.search(text)
    if not m:
        return None
    day = int(m.group(1))
    month_str = (m.group(2) or "").strip().lower()
    year = int(m.group(3))
    hour = int(m.group(4)) if m.group(4) else 0
    minute = int(m.group(5)) if m.group(5) else 0
    month = MONTHS_IT.get(month_str)
    if not month:
        return None
    try:
        return datetime(year, month, day, hour, minute)
    except Exception:
        return None

def _find_date_near_link(soup: BeautifulSoup, link_tag):
    for parent in link_tag.parents:
        try:
            txt = parent.get_text(" ", strip=True)
        except Exception:
            txt = ""
        dt = _parse_italian_datetime_from_text(txt)
        if dt:
            return dt
    for parent in link_tag.parents:
        try:
            times = parent.find_all("time")
        except Exception:
            times = []
        for t in times:
            iso = t.get("datetime")
            if iso:
                try:
                    return datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
    return None

def _find_date_in_document(soup: BeautifulSoup):
    try:
        full_txt = soup.get_text(" ", strip=True)
    except Exception:
        full_txt = ""
    dt = _parse_italian_datetime_from_text(full_txt)
    if dt:
        return dt
    for t in soup.find_all("time"):
        iso = t.get("datetime")
        if iso:
            try:
                return datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
    return None

def get_zip_files(url):
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        links = soup.find_all("a", href=lambda href: href and href.lower().endswith(".zip"))
        unique_urls = []
        seen = set()
        for a in links:
            abs_url = urljoin(url, a["href"])
            if abs_url not in seen:
                unique_urls.append((a, abs_url))
                seen.add(abs_url)

        zip_files = []
        for link_tag, file_url in unique_urls:
            file_name = os.path.basename(file_url)
            mod_date = None

            mod_date = _find_date_near_link(soup, link_tag)

            if not mod_date:
                mod_date = _find_date_in_document(soup)

            if not mod_date:
                m = re.search(r"(\d+)_(\d{4})\.zip$", file_name)
                if m:
                    year = int(m.group(2))
                    mod_date = datetime(year, 1, 1, 0, 0)

            if not mod_date:
                mod_date = datetime(1900, 1, 1, 0, 0)

            zip_files.append({
                "date": mod_date,
                "name": file_name,
                "url": file_url,
                "found_pdfs": []
            })
        return zip_files
    except requests.exceptions.RequestException:
        return None

def find_string_in_pdfs(zip_url, search_strings):
    found_pdfs_with_words = []
    search_pattern = "|".join(re.escape(s) for s in search_strings)
    
    try:
        with requests.get(zip_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_zip_path = os.path.join(tmpdir, "temp.zip")
                with open(tmp_zip_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)

                try:
                    with zipfile.ZipFile(tmp_zip_path, "r") as zip_ref:
                        for filename in zip_ref.namelist():
                            if filename.lower().endswith(".pdf"):
                                with zip_ref.open(filename, "r") as pdf_file:
                                    reader = PdfReader(pdf_file)
                                    text_content = ""
                                    for page in reader.pages:
                                        text_content += page.extract_text() or ""
                                    
                                    match = re.search(search_pattern, text_content, re.IGNORECASE)
                                    if match:
                                        found_word = match.group(0)
                                        found_pdfs_with_words.append((filename, found_word))
                except zipfile.BadZipFile:
                    pass
    except Exception:
        pass
    return found_pdfs_with_words

def create_output_content(file_list, html_format=False):
    output_lines = []
    processed_pdfs = set()
    last_date = None
    
    if not file_list:
        return "Nessun file .zip trovato." if not html_format else "<html><body><p>Nessun file .zip trovato.</p></body></html>"

    for file_info in file_list:
        current_date = file_info["date"].date()
        if last_date and current_date != last_date:
            output_lines.append("..................................................")
        last_date = current_date

        date_str = file_info["date"].strftime("%Y-%m-%d %H:%M") if isinstance(file_info["date"], datetime) else "Data non trovata"
        output_lines.append(f"{date_str} --- {file_info['name']}")

        if file_info["found_pdfs"]:
            pdfs_to_add = []
            for pdf_name, found_word in file_info["found_pdfs"]:
                if (pdf_name, found_word) not in processed_pdfs:
                    pdfs_to_add.append((pdf_name, found_word))
                    processed_pdfs.add((pdf_name, found_word))
            
            if pdfs_to_add:
                output_lines.append("-" * 50)
                for pdf_name, found_word in pdfs_to_add:
                    output_lines.append(f"{pdf_name} (<b>{found_word}</b>)")
                output_lines.append("-" * 50)
    
    if html_format:
        current_time = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
        content = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoraggio</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; padding: 10px; }}
        .item {{ margin-bottom: 20px; }}
        .separator {{ margin: 10px 0; border: 0; border-top: 1px solid #ccc; }}
        .file-entry {{ margin-bottom: 5px; }}
        @media (max-width: 600px) {{
            body {{
                line-height: 1.0;
            }}
        }}
    </style>
</head>
<body>
    <h1>Elenco .zip alle {current_time}</h1>
"""
        for line in output_lines:
            if line.startswith('---'):
                content += '    <hr class="separator">\n'
            elif line.startswith('....'):
                content += '    <hr class="separator">\n'
            else:
                content += f"    <p>{line}</p>\n"
        content += """
</body>
</html>"""
        return content
    else:
        return "\n".join(output_lines)

def update_github_file(repo_owner, repo_name, file_path, new_content, commit_message):
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
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
        except Exception:
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=new_content,
                branch="main"
            )
    except Exception as e:
        print(f"Errore durante l'aggiornamento del file su GitHub: {e}")

if __name__ == "__main__":
    REPO_OWNER = "Sebastiano-Mazzarisi"
    REPO_NAME = "Test"
    
    zip_files = get_zip_files(ROOT_URL)
    
    if zip_files is not None:
        zip_files.sort(key=lambda x: x["date"], reverse=True)
        if len(zip_files) > 15:
            zip_files = zip_files[:15]
            
        for fi in zip_files:
            fi["found_pdfs"] = find_string_in_pdfs(fi["url"], SEARCH_STRINGS)

        html_output = create_output_content(zip_files, html_format=True)
        commit_msg = "Aggiornamento automatico elenco file .zip"
        
        update_github_file(REPO_OWNER, REPO_NAME, FILE_PATH, html_output, commit_msg)
        print("Il programma ha terminato l'esecuzione. L'output è stato caricato su GitHub.")