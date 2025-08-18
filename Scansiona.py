import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import zipfile
import tempfile
import shutil
import re
from PyPDF2 import PdfReader
import logging
from urllib.parse import urljoin

# Configurazione per sopprimere gli avvisi di PyPDF2
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

# --- Configurazione per Test in Locale ---
FILE_PATH = "Monitorizza.html"
SEARCH_STRING = "Vetrugno"
# --- ---

def get_zip_files(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        links = soup.find_all('a', href=lambda href: href and href.endswith('.zip'))
        unique_urls = set(urljoin(url, link['href']) for link in links)
        
        zip_files = []
        for file_url in unique_urls:
            
            file_name = os.path.basename(file_url)
            mod_date = datetime(1900, 1, 1)

            link_tag = soup.find('a', href=file_url)
            
            if link_tag:
                date_tag = link_tag.find_previous(lambda tag: 'Pubblicato:' in tag.get_text())
                if date_tag:
                    date_str = date_tag.get_text().strip()
                    try:
                        months_ita_to_eng = {
                            "gennaio": "January", "febbraio": "February", "marzo": "March",
                            "aprile": "April", "maggio": "May", "giugno": "June",
                            "luglio": "July", "agosto": "August", "settembre": "September",
                            "ottobre": "October", "novembre": "November", "dicembre": "December"
                        }
                        
                        for ita, eng in months_ita_to_eng.items():
                            date_str = date_str.replace(ita, eng)
                        
                        date_part = re.search(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+\d{1,2}:\d{2}', date_str)
                        if date_part:
                            mod_date = datetime.strptime(date_part.group(), '%d %B %Y %H:%M')
                    except (ValueError, IndexError):
                        pass

            zip_files.append({
                "date": mod_date, 
                "name": file_name,
                "url": file_url,
                "found_pdfs": []
            })
            
        return zip_files
    except requests.exceptions.RequestException:
        return None

def find_string_in_pdfs(zip_url, search_string):
    found_pdfs = []
    try:
        with requests.get(zip_url, stream=True) as r:
            r.raise_for_status()
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_zip_path = os.path.join(tmpdir, "temp.zip")
                with open(tmp_zip_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

                try:
                    with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                        for filename in zip_ref.namelist():
                            if filename.lower().endswith('.pdf'):
                                with zip_ref.open(filename, 'r') as pdf_file: 
                                    reader = PdfReader(pdf_file)
                                    text_content = ""
                                    for page in reader.pages:
                                        text_content += page.extract_text() or ""
                                    
                                    if re.search(search_string, text_content, re.IGNORECASE):
                                        found_pdfs.append(filename)
                except zipfile.BadZipFile:
                    pass
    except Exception:
        pass
    return found_pdfs

def create_output_content(file_list, html_format=False):
    output_lines = []
    processed_pdfs = set()
    
    if not file_list:
        return "Nessun file .zip trovato." if not html_format else "<html><body><p>Nessun file .zip trovato.</p></body></html>"

    for file_info in file_list:
        date_str = file_info["date"].strftime('%Y-%m-%d') if isinstance(file_info["date"], datetime) else "Data non trovata"
        output_lines.append(f"{date_str} --- {file_info['name']}")
        
        if file_info['found_pdfs']:
            pdfs_to_add = [pdf for pdf in file_info['found_pdfs'] if pdf not in processed_pdfs]
            
            if pdfs_to_add:
                output_lines.append("-" * 50)
                for pdf_name in pdfs_to_add:
                    output_lines.append(pdf_name)
                    processed_pdfs.add(pdf_name)
                output_lines.append("-" * 50)

    if html_format:
        content = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoraggio</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 10px; }
        .item { margin-bottom: 20px; }
        .separator { margin: 10px 0; border: 0; border-top: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>Elenco file .zip aggiornato</h1>
"""
        for line in output_lines:
            if line.startswith('---'):
                content += '    <hr class="separator">\n'
            else:
                content += f"    <p>{line}</p>\n"
        content += """
</body>
</html>"""
        return content
    else:
        return "\n".join(output_lines)

def save_local_file(file_path, content):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"File '{file_path}' salvato con successo nella cartella corrente.")
    except Exception as e:
        print(f"Errore durante il salvataggio del file: {e}")

if __name__ == "__main__":
    URL_TO_SCRAPE = "https://www.pugliausr.gov.it/"
    
    zip_files = get_zip_files(URL_TO_SCRAPE)
    
    if zip_files is not None:
        zip_files.sort(key=lambda x: x['date'], reverse=True)
        
        if len(zip_files) > 15:
            zip_files = zip_files[:15]

        for file_info in zip_files:
            file_info["found_pdfs"] = find_string_in_pdfs(file_info['url'], SEARCH_STRING)
        
        text_output = create_output_content(zip_files)
        print(text_output)
        
        html_output = create_output_content(zip_files, html_format=True)
        save_local_file(FILE_PATH, html_output)