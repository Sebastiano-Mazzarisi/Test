import csv
import json
import os
import sys
import webbrowser
from datetime import datetime
from itertools import groupby
from github import Github
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

# Nome: Feste.py
# Data ultima modifica: 15/01/2026 
# FIX: Risolto bug tasto filtro non cliccabile (Z-Index) + Anti-Cache.

# Configurazione dei file
INPUT_FILE = 'Feste-elenco.csv'
BACKUP_FILE = 'Feste-backup.csv'
OUTPUT_FILE = 'Feste.html'
OUTPUT_TXT = 'Feste.txt'

# --- CONFIGURAZIONE GITHUB PROTETTA ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "Sebastiano-Mazzarisi/Test"

if not GITHUB_TOKEN:
    print("⚠️ ATTENZIONE: Token GitHub non trovato! Assicurati di aver creato il file .env")
# -----------------------------------------------------

ICON_URL = "https://sebastiano-mazzarisi.github.io/Test/Feste.png?v=12"
TXT_URL = "https://sebastiano-mazzarisi.github.io/Test/Feste.txt"


def aggiorna_github():
    """
    Funzione per caricare HTML, TXT, CSV e Script su GitHub.
    """
    if not GITHUB_TOKEN:
        print("❌ Impossibile aggiornare GitHub: Token mancante (controlla il file .env).")
        return

    print("\n☁️  Inizio aggiornamento GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    files_to_upload = [OUTPUT_FILE, OUTPUT_TXT, INPUT_FILE, "Feste.py"]

    for filename in files_to_upload:
        try:
            print(f"   ⬆️ Sto caricando {filename}...")
            
            if not os.path.exists(filename):
                print(f"   ⚠️ File {filename} non trovato in locale, salto l'upload.")
                continue

            with open(filename, 'r', encoding='utf-8') as f:
                contenuto = f.read()
            
            try:
                contents = repo.get_contents(filename)
                repo.update_file(contents.path, f"Aggiornamento {datetime.now()}", contenuto, contents.sha)
                print(f"   ✅ {filename} aggiornato con successo!")
            except:
                repo.create_file(filename, f"Creazione iniziale {filename}", contenuto)
                print(f"   ✅ {filename} creato con successo!")
                
        except Exception as e:
            print(f"   ❌ Errore upload {filename}: {e}")
    
    print("☁️  Operazioni GitHub terminate.\n")


def leggi_e_processa_dati(nome_file):
    dati = []
    fieldnames_found = []

    if not os.path.exists(nome_file):
        print(f"❌ Errore: Il file '{nome_file}' non è stato trovato.")
        return []

    try:
        with open(nome_file, mode='r', encoding='utf-8-sig') as f:
            content = f.read()
            f.seek(0)
            delimiter = ',' 
            if ';' in content and content.count(';') > content.count(','):
                delimiter = ';'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            if reader.fieldnames:
                reader.fieldnames = [name.strip() for name in reader.fieldnames]
                fieldnames_found = reader.fieldnames
            
            for row in reader:
                clean_row = {}
                for k, v in row.items():
                    if k:
                        clean_row[k] = v.strip() if v else ""
                
                cognome = clean_row.get('Cognome', '')
                nome = clean_row.get('Nome', '')
                
                if not cognome and not nome:
                    continue
                
                dati.append(clean_row)

        dati.sort(key=lambda x: (x.get('Cognome', '').lower(), x.get('Nome', '').lower()))
        print(f"✅ Letti e ordinati {len(dati)} record validi.")

        try:
            with open(BACKUP_FILE, mode='w', newline='', encoding='utf-8') as fb:
                writer = csv.DictWriter(fb, fieldnames=fieldnames_found)
                writer.writeheader()
                writer.writerows(dati)
            print(f"💾 Backup creato con successo: {BACKUP_FILE}")
        except Exception as e_backup:
            print(f"⚠️ Attenzione: Impossibile creare il file di backup: {e_backup}")

        return dati

    except Exception as e:
        print(f"❌ Errore durante la lettura del CSV: {e}")
        return []

def formatta_eventi_gruppo(gruppo_eventi):
    lines = []
    skip_indices = set()
    
    for i, e in enumerate(gruppo_eventi):
        if i in skip_indices: continue
        phrase = ""
        if e['Tipo'] == 'Anniversario':
            match_index = -1
            for j in range(i + 1, len(gruppo_eventi)):
                other = gruppo_eventi[j]
                if j not in skip_indices and other['Tipo'] == 'Anniversario' and other['Years'] == e['Years']:
                    match_index = j
                    break
            if match_index != -1:
                partner = gruppo_eventi[match_index]
                skip_indices.add(match_index)
                nomi = sorted([f"{e['Nome']} {e['Cognome']}", f"{partner['Nome']} {partner['Cognome']}"])
                phrase = f"Anniversario di {nomi[0]} e {nomi[1]}"
                if e['Years']: phrase += f" ({e['Years']} anni)"
            else:
                phrase = f"Anniversario di {e['Nome']} {e['Cognome']}"
                if e['Years']: phrase += f" ({e['Years']} anni)"
        elif e['Tipo'] == 'Compleanno':
            phrase = f"{e['Nome']} {e['Cognome']} festeggia il compleanno"
            if e['Years']: phrase += f" e compie {e['Years']} anni"
        elif e['Tipo'] == 'Onomastico':
            phrase = f"È l'onomastico di {e['Nome']} {e['Cognome']}"
        phrase += "."
        lines.append(phrase)
    return lines

def genera_txt_siri_discorsivo(dati, fake_today=None):
    if fake_today:
        today = fake_today.replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"🗣️ Generazione Siri simulando data: {today.strftime('%d/%m/%Y')}")
    else:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        print("🗣️ Generazione Siri con data odierna reale.")

    mesi_nomi = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", 
                 "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    giorni_nomi = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    
    processed_events = []
    for item in dati:
        try:
            parts = item.get('Data', '').split('/')
            if len(parts) < 2: continue
            day, month = int(parts[0]), int(parts[1])
            year_str = parts[2] if len(parts) > 2 and parts[2] else None
            try:
                next_event = datetime(today.year, month, day)
            except ValueError: continue 
            if next_event < today: next_event = next_event.replace(year=today.year + 1)
            days_until = (next_event - today).days
            weekday_index = next_event.weekday()
            weekday_name = giorni_nomi[weekday_index]
            years_turning = None
            if year_str:
                origin_year = int(year_str)
                years_turning = next_event.year - origin_year
            tipo = item.get('Festa', 'Anniversario')
            if tipo not in ['Compleanno', 'Onomastico']: tipo = 'Anniversario'
            processed_events.append({
                'Nome': item.get('Nome', ''),
                'Cognome': item.get('Cognome', ''),
                'Tipo': tipo,
                'DaysUntil': days_until,
                'Years': years_turning,
                'Day': day,
                'MonthName': mesi_nomi[month],
                'WeekdayName': weekday_name
            })
        except: continue

    processed_events.sort(key=lambda x: x['DaysUntil'])

    lines = []
    if fake_today: lines.append(f"Riepilogo feste (Simulazione al {today.strftime('%d/%m/%Y')}).\n")
    else: lines.append("Ecco il riepilogo delle feste.\n")

    events_today = [e for e in processed_events if e['DaysUntil'] == 0]
    today_weekday = giorni_nomi[today.weekday()]
    today_month = mesi_nomi[today.month]
    today_str_full = f"{today_weekday} {today.day} {today_month}"

    if events_today:
        lines.append("Attenzione, oggi c'è una festa!")
        today_date_str = f"Oggi, {today_str_full},"
        lines.append(today_date_str)
        frasi_oggi = formatta_eventi_gruppo(events_today)
        lines.extend(frasi_oggi)
    else:
        lines.append(f"Oggi, {today_str_full}, nessun evento in programma.")
    lines.append("\n") 

    upcoming = [e for e in processed_events if e['DaysUntil'] > 0][:8] 
    if upcoming:
        lines.append("Nei prossimi giorni:")
        groups = []
        for k, g in groupby(upcoming, key=lambda x: x['DaysUntil']):
            groups.append(list(g))
        for i, group in enumerate(groups):
            first = group[0]
            if i == 1: lines.append("\nE ancora:")
            elif i > 1: lines.append("") 
            date_string = f"{first['WeekdayName']} {first['Day']} {first['MonthName']}"
            if first['DaysUntil'] == 1: header = f"Domani, {date_string},"
            else: header = f"Tra {first['DaysUntil']} giorni, {date_string},"
            lines.append(header)
            frasi_gruppo = formatta_eventi_gruppo(group)
            lines.extend(frasi_gruppo)
    else:
        lines.append("Non ci sono altri eventi imminenti.")

    try:
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"📄 File Siri ACCORPATO generato: {OUTPUT_TXT}")
    except Exception as e:
        print(f"⚠️ Errore scrittura file Siri: {e}")

def genera_html(dati, fake_today=None):
    json_dati = json.dumps(dati, ensure_ascii=False)
    
    try:
        with open(OUTPUT_TXT, 'r', encoding='utf-8') as f:
            siri_text_js = json.dumps(f.read(), ensure_ascii=False)
    except:
        siri_text_js = '""'
        print("⚠️ Attenzione: File TXT Siri non trovato durante la generazione HTML.")
    
    if fake_today:
        js_date_code = f"new Date({fake_today.year}, {fake_today.month - 1}, {fake_today.day})"
        timestamp_str = datetime.now().strftime("%d/%m/%Y - %H:%M:%S") + " (Simulato)"
    else:
        js_date_code = "new Date()"
        timestamp_str = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">

    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Feste</title>
    
    <link rel="icon" type="image/png" href="{ICON_URL}">
    <link rel="apple-touch-icon" href="{ICON_URL}">
    <meta property="og:image" content="{ICON_URL}">
    <meta name="theme-color" content="#2563eb">
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    
    <style>
        :root {{
            --primary: #2563eb;       
            --primary-dark: #1e40af;
            --primary-light: #eff6ff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --bg-body: #f1f5f9;      
            --bg-yellowish: #fffbeb; 
            --bg-card: #ffffff;
            
            --bg-past-green: #dcfce7;
            --border-past-green: #86efac;
            --text-past-green: #14532d;
            
            --today-bg: #fef2f2;
            --today-border: #ef4444;
            --border-color: #cbd5e1;
            
            --color-compleanno: #003366; 
            --color-onomastico: #006400; 
            --color-anniversario: #990033; 
        }}
        
        html {{ font-size: 16px; }} 
        @media (min-width: 768px) {{ html {{ font-size: 20px; }} }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-body); 
            color: var(--text-main);
            display: flex;
            justify-content: center;
            min-height: 100vh;
            overscroll-behavior-y: contain;
        }}

        .app-container {{
            width: 100%;
            max-width: 600px;
            background-color: var(--bg-body);
            min-height: 100vh;
            position: relative;
            padding-bottom: 100px; 
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            transition: background-color 0.3s ease;
        }}
        .app-container.bg-yellow-mode {{ background-color: var(--bg-yellowish) !important; }}

        .header {{
            background-color: var(--primary); 
            color: white;                     
            padding: 1.5rem;
            position: sticky;
            top: 0;
            z-index: 50;
            text-align: center;              
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }}
        .header-content {{ position: relative; max-width: 100%; }}
        .header h1 {{ font-size: 1.6rem; font-weight: 800; margin: 0; letter-spacing: 0.5px; text-transform: uppercase; }}
        .header p {{ font-size: 0.95rem; opacity: 0.9; margin-top: 5px; font-weight: 400; }}
        
        .header-btn {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: white; 
            border: none;
            color: var(--primary); 
            font-size: 1.4rem;
            cursor: pointer;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s, transform 0.2s;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            /* FIX CRUCIALE: Z-INDEX ALTO PER STARE SOPRA IL TESTO CENTRALE */
            z-index: 100;
        }}
        .header-btn:hover {{ background: #f8fafc; transform: translateY(-50%) scale(1.05); }}
        .print-btn {{ right: 0; }}
        .filter-btn {{ left: 0; }}

        /* --- MODAL --- */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.6);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(4px);
            opacity: 0;
            transition: opacity 0.3s;
        }}
        .modal-overlay.open {{ display: flex; opacity: 1; }}

        .modal-box {{
            background: white;
            width: 90%;
            max-width: 340px;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            transform: scale(0.9);
            transition: transform 0.3s;
        }}
        .modal-overlay.open .modal-box {{ transform: scale(1); }}
        .modal-title {{ font-size: 1.2rem; font-weight: 800; margin-bottom: 20px; color: var(--primary); text-align: center; text-transform: uppercase; }}

        .print-options {{ display: flex; flex-direction: column; gap: 12px; }}
        .print-option-btn {{ background: white; border: 2px solid var(--primary); color: var(--primary); padding: 12px; border-radius: 12px; font-size: 1rem; font-weight: 700; cursor: pointer; transition: all 0.2s; text-align: left; display: flex; align-items: center; gap: 10px; }}
        .print-option-btn:hover {{ background: var(--primary-light); }}
        .print-option-btn span {{ font-size: 1.2rem; }}

        .stats-scroll-box {{ max-height: 50vh; overflow-y: auto; margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; }}
        .stat-entry {{ padding: 8px 0; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; font-size: 0.95rem; color: var(--text-main); }}
        .stat-entry:last-child {{ border-bottom: none; }}
        .clickable-stat {{ cursor: pointer; transition: opacity 0.2s; }}
        .clickable-stat:hover {{ opacity: 0.7; }}

        .checkbox-container {{ display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px; }}
        .checkbox-item {{ display: flex; align-items: center; font-size: 1.1rem; color: var(--text-main); cursor: pointer; padding: 8px; border-radius: 8px; transition: background 0.2s; }}
        .checkbox-item:hover {{ background: var(--bg-body); }}
        .checkbox-item input[type="checkbox"] {{ width: 22px; height: 22px; margin-right: 15px; accent-color: var(--primary); cursor: pointer; }}

        .modal-actions {{ display: flex; justify-content: center; margin-top:15px; }}
        .modal-btn {{ background: var(--primary); color: white; border: none; padding: 10px 30px; font-size: 1rem; font-weight: 700; border-radius: 30px; cursor: pointer; width: 100%; }}

        /* --- TABS --- */
        .tab-content {{ display: none; padding: 1rem; animation: fadeIn 0.3s ease; }}
        .tab-content.active {{ display: block; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 3px 6px rgba(0,0,0,0.05); transition: background-color 0.3s; }}
        
        /* STILI EVENTI */
        .is-past {{ 
            background-color: var(--bg-past-green) !important; 
            border-color: var(--border-past-green) !important;
        }}
        .is-past .cal-date {{ opacity: 0.6; color: var(--text-past-green); }} 
        .is-past .cal-name {{ opacity: 0.8; color: var(--text-past-green); }}
        .is-past .cal-type {{ opacity: 0.7; color: var(--text-past-green); }}
        .is-past .home-badge {{ display: none; }}

        .is-today {{ background-color: var(--today-bg) !important; border-left-color: var(--today-border) !important; }}
        .is-today .days-label {{ color: var(--today-border) !important; font-weight: 900; }}

        .cal-date {{ width: 60px; text-align: center; font-weight: 800; font-size: 1.3rem; color: var(--primary); line-height: 1.1; margin-right: 15px; display: flex; flex-direction: column; justify-content: center; }}
        .cal-date small {{ display: block; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); margin-top: 2px; }}
        
        .event-row {{ margin-bottom: 12px; position: relative; }}
        .event-row:last-child {{ margin-bottom: 0; }}
        .cal-name {{ font-weight: 700; font-size: 1.1rem; margin-bottom: 2px; line-height: 1.2; padding-right: 60px; }}
        
        .name-compleanno {{ color: var(--primary) !important; }} 
        .name-onomastico {{ color: var(--color-onomastico); }}
        .name-anniversario {{ color: var(--color-anniversario); }}

        .cal-type {{ font-size: 0.9rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }}
        .home-badge {{ position: absolute; top: 0; right: 0; background: var(--primary-light); color: var(--primary); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
        .bold-number {{ font-weight: 900; color: var(--text-main); }}

        .search-wrapper {{ display: flex; align-items: center; gap: 10px; margin-bottom: 1rem; }}
        .search-container {{ position: relative; flex-grow: 1; }}
        .search-box {{ width: 100%; padding: 12px 40px 12px 14px; border: 2px solid var(--border-color); border-radius: 12px; font-size: 1.1rem; outline: none; transition: border-color 0.2s; }}
        .search-box:focus {{ border-color: var(--primary); }}
        .search-clear {{ position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: #e2e8f0; border: none; color: #64748b; width: 24px; height: 24px; border-radius: 50%; font-size: 14px; font-weight: bold; cursor: pointer; display: none; align-items: center; justify-content: center; padding-bottom: 2px; }}
        .result-count {{ background: var(--primary); color: white; min-width: 50px; height: 50px; border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: 800; font-size: 1.4rem; line-height: 1; flex-shrink: 0; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2); }}

        .rubrica-item {{ background: white; border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 12px; padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
        .rubrica-name {{ font-weight: 800; font-size: 1.15rem; color: var(--text-main); margin-bottom: 6px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; }}
        .rubrica-row {{ display: flex; align-items: center; padding: 4px 2px; font-size: 0.95rem; }}
        .rubrica-row.is-past-row .rubrica-type, .rubrica-row.is-past-row .rubrica-date {{ opacity: 0.6; }}
        .rubrica-type {{ flex: 1; color: var(--text-muted); display: flex; align-items: center; gap: 8px; font-weight: 500; }}
        .rubrica-date {{ font-weight: 600; color: var(--text-main); font-size: 0.9rem; min-width: 80px; text-align: right; }}

        /* NAVIGAZIONE */
        .nav-bar {{ position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 600px; background: white; display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid var(--border-color); z-index: 100; padding-bottom: max(10px, env(safe-area-inset-bottom)); box-shadow: 0 -4px 20px rgba(0,0,0,0.05); }}
        .nav-item {{ border: none; background: none; display: flex; flex-direction: column; align-items: center; gap: 5px; color: var(--text-muted); font-size: 0.75rem; font-weight: 600; cursor: pointer; width: 33%; }} /* Width 33% perchè sono 3 item */
        .nav-item.active {{ color: var(--primary); }}
        .nav-item svg {{ width: 24px; height: 24px; stroke-width: 2.5px; }}

        #refresh-indicator {{ position: fixed; top: 70px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.8rem; z-index: 200; opacity: 0; transition: opacity 0.3s; pointer-events: none; }}
        #refresh-indicator.show {{ opacity: 1; }}

        #focus-target {{ scroll-margin-top: 45vh; }} /* Per centrare l'elemento */

    </style>
</head>
<body>
    
    <div id="refresh-indicator">Rilascia per aggiornare...</div>

    <div id="filter-modal" class="modal-overlay" onclick="closeFilterModal(event)">
        <div class="modal-box" onclick="event.stopPropagation()">
            <div class="modal-title">Filtra Gruppi</div>
            <div class="checkbox-container">
                <label class="checkbox-item"><input type="checkbox" id="chk-amici" value="A" checked onchange="updateFilters()"><span>Amici</span></label>
                <label class="checkbox-item"><input type="checkbox" id="chk-mazzarisi" value="M" checked onchange="updateFilters()"><span>Mazzarisi</span></label>
                <label class="checkbox-item"><input type="checkbox" id="chk-pricci" value="P" checked onchange="updateFilters()"><span>Pricci</span></label>
                <label class="checkbox-item"><input type="checkbox" id="chk-famiglia" value="F" checked onchange="updateFilters()"><span>Famiglia</span></label>
                <label class="checkbox-item"><input type="checkbox" id="chk-geometri" value="G" checked onchange="updateFilters()"><span>Geometri</span></label>
                <label class="checkbox-item"><input type="checkbox" id="chk-febbre" value="S" checked onchange="updateFilters()"><span>Febbre del sabato</span></label>
            </div>
            <div class="modal-actions">
                <button class="modal-btn" onclick="closeFilterModal(event)">Chiudi</button>
            </div>
        </div>
    </div>

    <div id="print-modal" class="modal-overlay" onclick="closePrintModal(event)">
        <div class="modal-box" onclick="event.stopPropagation()">
            <div class="modal-title">Scegli Formato Stampa</div>
            <div class="print-options">
                <button class="print-option-btn" onclick="generateRubricaPDF()">
                    <span>📖</span> 1) Rubrica
                </button>
                <button class="print-option-btn" onclick="generateCalendarMaxPDF()">
                    <span>🗓️</span> 2) Calendario Max
                </button>
                <button class="print-option-btn" onclick="generateCalendarMinPDF()">
                    <span>📄</span> 3) Calendario Min
                </button>
                <button class="print-option-btn" onclick="generateSiriPDF()">
                    <span>🤖</span> 4) Testo per Siri
                </button>
            </div>
            <div class="modal-actions">
                <button class="modal-btn" onclick="closePrintModal(event)">Annulla</button>
            </div>
        </div>
    </div>

    <div id="stats-modal" class="modal-overlay" onclick="closeStatsModal(event)">
        <div class="modal-box" onclick="event.stopPropagation()">
            <div class="modal-title" id="stats-title">Dettagli</div>
            <div id="stats-list" class="stats-scroll-box"></div>
            <div class="modal-actions">
                <button class="modal-btn" onclick="closeStatsModal(event)">Chiudi</button>
            </div>
        </div>
    </div>

    <div class="app-container" id="app-container">
        
        <div class="header">
            <div class="header-content">
                <button class="header-btn filter-btn" onclick="openFilterModal()" title="Elenco da spuntare">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
                </button>

                <h1>EVENTI E FESTE</h1>
                <p>{timestamp_str}</p>
                <button onclick="forceReload()" style="background:transparent; border:1px solid rgba(255,255,255,0.5); color:white; border-radius:20px; padding:4px 12px; font-size:0.8rem; margin-top:5px; cursor:pointer;">
                    ↻ Aggiorna ora
                </button>
                
                <button class="header-btn print-btn" onclick="openPrintModal()" title="Stampa PDF">
                    🖨️
                </button>
            </div>
        </div>

        <div id="tab-home" class="tab-content active">
            <div id="upcoming-list"></div>
        </div>

        <div id="tab-rubrica" class="tab-content">
            <div class="search-wrapper">
                <div class="search-container">
                    <input type="text" id="search-input" class="search-box" placeholder="Cerca..." oninput="handleSearchInput()">
                    <button id="search-clear" class="search-clear" onclick="clearSearch()">✕</button>
                </div>
                <div class="result-count" id="search-counter">
                    <div id="count-val">0</div>
                </div>
            </div>
            <div id="rubrica-list"></div>
        </div>

        <div id="tab-stats" class="tab-content">
            <div class="card">
                <h3 style="margin-bottom: 20px; font-size: 1.2rem;">Statistiche Mesi</h3>
                <div id="stats-months"></div>
            </div>
            <div class="card">
                <h3 style="margin-bottom: 20px; font-size: 1.2rem;">Tipologia</h3>
                <div id="stats-types"></div>
            </div>
            <div class="card">
                <h3 style="margin-bottom: 20px; font-size: 1.2rem;">Genere</h3>
                <div id="stats-gender"></div>
            </div>
            <div class="card">
                <h3 style="margin-bottom: 20px; font-size: 1.2rem;">Gruppi</h3>
                <div id="stats-groups"></div>
            </div>
        </div>

        <nav class="nav-bar">
            <button class="nav-item active" onclick="switchTab('home')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
                Home
            </button>
            <button class="nav-item" onclick="switchTab('rubrica')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                Rubrica
            </button>
            <button class="nav-item" onclick="switchTab('stats')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                Stats
            </button>
        </nav>

    </div>

    <script>
        const rawData = {json_dati};
        const REF_DATE = {js_date_code}; 
        const SIRI_TEXT = {siri_text_js};
        const TXT_URL_SOURCE = "{TXT_URL}";
        const months = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];
        const shortMonths = ['GEN', 'FEB', 'MAR', 'APR', 'MAG', 'GIU', 'LUG', 'AGO', 'SET', 'OTT', 'NOV', 'DIC'];
        
        let activeTabId = 'home';
        let events = [];
        
        // --- STATO SCROLL PER OGNI TAB ---
        let tabScrollPositions = {{ 'home': 0, 'rubrica': 0, 'stats': 0 }};
        let isFirstHomeLoad = true;

        const groupMap = {{ 'A': 'Amici', 'M': 'Mazzarisi', 'P': 'Pricci', 'F': 'Famiglia', 'G': 'Geometri', 'S': 'Febbre del sabato' }};

        // --- FUNZIONI DI UTILITÀ ---
        function openFilterModal() {{ document.getElementById('filter-modal').classList.add('open'); }}
        function closeFilterModal(e) {{ if(e) e.preventDefault(); document.getElementById('filter-modal').classList.remove('open'); }}
        function openPrintModal() {{ document.getElementById('print-modal').classList.add('open'); }}
        function closePrintModal(e) {{ if(e) e.preventDefault(); document.getElementById('print-modal').classList.remove('open'); }}

        function updateFilters() {{ calculateEvents(); renderHome(); renderRubrica(document.getElementById('search-input').value); renderStats(); }}

        function getSelectedGroups() {{
            const selected = [];
            if(document.getElementById('chk-amici').checked) selected.push('A');
            if(document.getElementById('chk-mazzarisi').checked) selected.push('M');
            if(document.getElementById('chk-pricci').checked) selected.push('P');
            if(document.getElementById('chk-famiglia').checked) selected.push('F');
            if(document.getElementById('chk-geometri').checked) selected.push('G');
            if(document.getElementById('chk-febbre').checked) selected.push('S');
            return selected;
        }}
        
        function getSelectedGroupNames() {{
            const codes = getSelectedGroups();
            if (codes.length === 0) return 'Nessun gruppo';
            return codes.map(c => groupMap[c]).join(', ');
        }}

        function parseDate(dateStr) {{
            if (!dateStr) return null;
            const parts = dateStr.split('/');
            if (parts.length < 2) return null;
            return {{ day: parseInt(parts[0]), month: parseInt(parts[1]), year: parts[2] || null }};
        }}

        function getEventInfo(parsedDate) {{
            const today = new Date(REF_DATE); 
            today.setHours(0,0,0,0);
            let eventDate = new Date(today.getFullYear(), parsedDate.month - 1, parsedDate.day);
            let isPast = false;
            if (eventDate < today) {{ isPast = true; eventDate.setFullYear(today.getFullYear() + 1); }}
            const diffTime = eventDate - today;
            const daysUntil = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Verifica se è passato QUEST'ANNO (per colorare di verde)
            const currentYearDate = new Date(today.getFullYear(), parsedDate.month - 1, parsedDate.day);
            const actuallyPastThisYear = currentYearDate.getTime() < today.getTime();
            
            return {{ daysUntil, actuallyPastThisYear }};
        }}

        function calculateEvents() {{
            const allowedGroups = getSelectedGroups();
            events = rawData.filter(item => {{
                const grp = (item.Gruppo || '').trim().toUpperCase();
                return allowedGroups.some(selected => grp.includes(selected));
            }}).map(item => {{
                const pDate = parseDate(item.Data);
                if (!pDate) return null;
                const info = getEventInfo(pDate);
                let tipo = item.Festa;
                if (tipo !== 'Compleanno' && tipo !== 'Onomastico') tipo = 'Anniversario';
                let yearsTurning = null;
                if (pDate.year) {{
                    const today = new Date(REF_DATE); 
                    const currentYear = today.getFullYear();
                    yearsTurning = currentYear - parseInt(pDate.year);
                }}
                let currentAge = yearsTurning;
                return {{ ...item, pDate, daysUntil: info.daysUntil, isPastThisYear: info.actuallyPastThisYear, tipoDisplay: tipo, yearsTurning: yearsTurning, currentAge: currentAge, Genere: item.Genere, Cognome: item.Cognome, Nome: item.Nome, Gruppo: item.Gruppo }};
            }}).filter(e => e !== null);
        }}

        function processDayEvents(dayEvents) {{
            const mergedList = [];
            const skipIndices = new Set();
            for (let i = 0; i < dayEvents.length; i++) {{
                if (skipIndices.has(i)) continue;
                const e1 = dayEvents[i];
                let merged = null;
                if (e1.tipoDisplay === 'Anniversario') {{
                    let matchIdx = -1;
                    for (let j = i + 1; j < dayEvents.length; j++) {{
                        if (skipIndices.has(j)) continue;
                        const e2 = dayEvents[j];
                        if (e2.tipoDisplay === 'Anniversario' && e2.pDate.year === e1.pDate.year) {{
                            const g1 = e1.Genere ? e1.Genere.toUpperCase().trim() : '';
                            const g2 = e2.Genere ? e2.Genere.toUpperCase().trim() : '';
                            if (g1 !== g2) {{ matchIdx = j; break; }}
                        }}
                    }}
                    if (matchIdx !== -1) {{
                        const e2 = dayEvents[matchIdx];
                        skipIndices.add(matchIdx);
                        let fEvent = e1; 
                        let mEvent = e2;
                        if (e1.Genere && e1.Genere.toUpperCase().trim() === 'M') {{ fEvent = e2; mEvent = e1; }} 
                        merged = {{ isMerged: true, l1: `${{fEvent.Nome}} ${{fEvent.Cognome}}`, l2: `${{mEvent.Nome}} ${{mEvent.Cognome}}`, lbl: `Anniversario${{e1.yearsTurning !== null ? ' (' + e1.yearsTurning + ')' : ''}}`, type: 'Anniversario' }};
                    }}
                }}
                if (merged) {{ mergedList.push(merged); }} 
                else {{ mergedList.push({{ isMerged: false, l1: `${{e1.Nome}} ${{e1.Cognome}}`, lbl: e1.tipoDisplay + (e1.yearsTurning !== null ? ` (${{e1.yearsTurning}})` : ''), type: e1.tipoDisplay }}); }}
            }}
            const priority = {{ 'Compleanno': 1, 'Anniversario': 2, 'Onomastico': 3 }};
            mergedList.sort((a, b) => {{ const pA = priority[a.type] || 99; const pB = priority[b.type] || 99; return pA - pB; }});
            return mergedList;
        }}
        
        function fmtLbl(label) {{ return label.replace(/(\\(\\d+\\))/, '<span class="bold-number">$1</span>'); }}
        function getCls(type) {{
            if (type === 'Compleanno') return 'name-compleanno';
            if (type === 'Onomastico') return 'name-onomastico';
            if (type === 'Anniversario') return 'name-anniversario';
            return '';
        }}

        function renderHome() {{
            const container = document.getElementById('upcoming-list');
            
            // Ordina per Mese e Giorno (1 Gen -> 31 Dic)
            const sortedEvents = [...events].sort((a, b) => {{
                if (a.pDate.month !== b.pDate.month) return a.pDate.month - b.pDate.month;
                return a.pDate.day - b.pDate.day;
            }});

            if (sortedEvents.length === 0) {{ container.innerHTML = '<div style="text-align:center; padding:2rem; font-size:1rem; color:var(--text-muted)">Nessun evento per i gruppi selezionati</div>'; return; }}
            
            const groupedByDate = {{}};
            const uniqueDates = [];
            sortedEvents.forEach(e => {{ 
                const dateKey = `${{e.pDate.month}}-${{e.pDate.day}}`; 
                if (!groupedByDate[dateKey]) {{ groupedByDate[dateKey] = []; uniqueDates.push(e); }} 
                groupedByDate[dateKey].push(e); 
            }});
            
            let focusTargetSet = false;

            container.innerHTML = uniqueDates.map(refEvent => {{
                const dateKey = `${{refEvent.pDate.month}}-${{refEvent.pDate.day}}`;
                const dayEvents = groupedByDate[dateKey];
                const processed = processDayEvents(dayEvents);
                
                let dayLabel = refEvent.daysUntil + ' gg';
                let cardClass = 'card';
                let borderStyle = 'border-left: 5px solid var(--primary);';
                
                // Gestione stili Passato/Oggi/Futuro
                if (refEvent.isPastThisYear) {{
                    cardClass += ' is-past';
                    dayLabel = ""; 
                    borderStyle = 'border-left: 5px solid var(--border-past-green);';
                }} 
                else if (refEvent.daysUntil === 0) {{ 
                    dayLabel = "OGGI!"; 
                    cardClass += ' is-today'; 
                }} 
                else if (refEvent.daysUntil === 1) {{ 
                    dayLabel = "Domani"; 
                }}
                
                // Determina ID per lo scroll (Il primo evento NON passato)
                let divId = "";
                if (!focusTargetSet && !refEvent.isPastThisYear) {{
                    divId = 'id="focus-target"';
                    focusTargetSet = true;
                }}
                
                const badgeHtml = dayLabel ? `<div class="home-badge">${{dayLabel}}</div>` : '';
                
                const eventsHtml = processed.map(item => {{
                    const icon = item.type === 'Compleanno' ? '🎂' : (item.type === 'Onomastico' ? '🌟' : '🍾');
                    const labelHtml = fmtLbl(item.lbl);
                    const colorClass = refEvent.isPastThisYear ? '' : getCls(item.type);
                    
                    if (item.isMerged) {{ 
                        return `<div class="event-row"><div class="cal-name ${{colorClass}}">${{item.l1}}</div><div class="cal-name ${{colorClass}}">${{item.l2}}</div><div class="cal-type"><span>${{icon}} ${{labelHtml}}</span></div></div>`; 
                    }} else {{ 
                        return `<div class="event-row"><div class="cal-name ${{colorClass}}">${{item.l1}}</div><div class="cal-type"><span>${{icon}} ${{labelHtml}}</span></div></div>`; 
                    }}
                }}).join('');
                
                return `<div class="${{cardClass}}" ${{divId}} style="display:flex; gap:15px; ${{borderStyle}} align-items:stretch;"><div class="cal-date"><div style="font-weight:800; font-size:1.5rem; line-height:1;">${{refEvent.pDate.day}}</div><div style="font-size:0.75rem; text-transform:uppercase; font-weight:600;">${{shortMonths[refEvent.pDate.month-1]}}</div></div><div style="flex:1; display:flex; flex-direction:column; justify-content:center; position: relative;">${{badgeHtml}}${{eventsHtml}}</div></div>`;
            }}).join('');
        }}

        function renderRubrica(filterText = '') {{
            const container = document.getElementById('rubrica-list');
            const countEl = document.getElementById('count-val');
            const clearBtn = document.getElementById('search-clear');
            const txt = filterText.toLowerCase();
            if (txt.length > 0) clearBtn.style.display = 'flex'; else clearBtn.style.display = 'none';
            const people = getGroupedPeople();
            const sortedPeople = Object.values(people).sort((a,b) => a.c.localeCompare(b.c));
            const filtered = sortedPeople.filter(p => p.n.toLowerCase().includes(txt) || p.c.toLowerCase().includes(txt));
            countEl.innerText = filtered.length;
            if (filtered.length === 0) {{ container.innerHTML = '<p style="text-align:center; padding:2rem; color:var(--text-muted); font-size:1rem;">Nessun risultato</p>'; return; }}
            container.innerHTML = filtered.map(p => {{
                const typePriority = {{ 'Compleanno': 1, 'Onomastico': 2, 'Anniversario': 3 }};
                p.i.sort((a, b) => typePriority[a.tipoDisplay] - typePriority[b.tipoDisplay]);
                const itemsHtml = p.i.map(i => {{
                    const icon = i.tipoDisplay === 'Compleanno' ? '🎂' : (i.tipoDisplay === 'Onomastico' ? '🌟' : '🍾');
                    let dateStr = '';
                    if (i.tipoDisplay === 'Onomastico') {{ dateStr = `${{i.pDate.day}} ${{months[i.pDate.month - 1].toLowerCase()}}`; }} 
                    else {{ dateStr = `${{i.pDate.day}}/${{i.pDate.month}}`; if (i.pDate.year) {{ dateStr += `/${{i.pDate.year}}`; }} }}
                    let rowClass = 'rubrica-row';
                    if (i.isPastThisYear) rowClass += ' is-past-row';
                    let displayLabel = i.tipoDisplay;
                    if (i.currentAge !== null && (i.tipoDisplay === 'Compleanno' || i.tipoDisplay === 'Anniversario')) {{ displayLabel += ` (${{i.currentAge}})`; }}
                    displayLabel = fmtLbl(displayLabel);
                    return `<div class="${{rowClass}}"><div class="rubrica-type"><span>${{icon}}</span><span>${{displayLabel}}</span></div><div class="rubrica-date">${{dateStr}}</div></div>`;
                }}).join('');
                return `<div class="rubrica-item"><div class="rubrica-name">${{p.c}} ${{p.n}}</div><div>${{itemsHtml}}</div></div>`;
            }}).join('');
        }}
        
        function getGroupedPeople() {{
            const people = {{}};
            events.forEach(e => {{ const key = e.Cognome + ' ' + e.Nome; if (!people[key]) people[key] = {{ c: e.Cognome, n: e.Nome, i: [] }}; people[key].i.push(e); }});
            return people;
        }}
        
        function handleSearchInput() {{
            const val = document.getElementById('search-input').value;
            renderRubrica(val);
        }}

        function clearSearch() {{ const input = document.getElementById('search-input'); input.value = ''; input.focus(); renderRubrica(''); }}
        
        // --- FUNZIONI DI STATISTICA E MODALI (STATS) ---
        function openStatsModal(type, value, title) {{
            const listEl = document.getElementById('stats-list');
            let displayTitle = title;
            if (type === 'month') {{ displayTitle = months[value]; }}
            document.getElementById('stats-title').innerText = displayTitle;
            listEl.innerHTML = '';
            
            let filteredList = [];
            if (type === 'month') {{ filteredList = events.filter(e => e.pDate.month === (value + 1)); }} 
            else if (type === 'type') {{ filteredList = events.filter(e => e.tipoDisplay === value); }} 
            else if (type === 'gender') {{ filteredList = events.filter(e => {{ const g = e.Genere ? e.Genere.toUpperCase().trim() : 'M'; return g === value; }}); }}
            else if (type === 'group') {{ filteredList = events.filter(e => {{ const g = (e.Gruppo || '').toUpperCase(); return g.includes(value); }}); }}
            
            const uniqueSet = new Set();
            const uniqueArr = [];
            filteredList.forEach(e => {{ const k = e.Cognome + '|' + e.Nome; if(!uniqueSet.has(k)) {{ uniqueSet.add(k); uniqueArr.push(e); }} }});
            filteredList = uniqueArr;
            filteredList.sort((a,b) => {{ if (a.Cognome.toLowerCase() !== b.Cognome.toLowerCase()) return a.Cognome.localeCompare(b.Cognome); return a.Nome.localeCompare(b.Nome); }});
            
            if (filteredList.length === 0) {{ listEl.innerHTML = '<div style="text-align:center;color:#666;padding:20px;">Nessun risultato</div>'; }} 
            else {{
                filteredList.forEach((e, index) => {{
                    const div = document.createElement('div');
                    div.className = 'stat-entry';
                    div.innerHTML = `<div>${{index + 1}}) ${{e.Cognome}} ${{e.Nome}}</div>`;
                    listEl.appendChild(div);
                }});
            }}
            document.getElementById('stats-modal').classList.add('open');
        }}
        function closeStatsModal(e) {{ if(e) e.preventDefault(); document.getElementById('stats-modal').classList.remove('open'); }}

        function renderStats() {{
            const mSets = Array.from({{length: 12}}, () => new Set());
            events.forEach(e => {{ const k = e.Cognome + '|' + e.Nome; mSets[e.pDate.month - 1].add(k); }});
            const mCount = mSets.map(s => s.size);
            const maxM = Math.max(...mCount) || 1;
            document.getElementById('stats-months').innerHTML = months.map((m, i) => {{
                if (mCount[i] === 0) return ''; const w = (mCount[i]/maxM)*100;
                return `<div class="clickable-stat" onclick="openStatsModal('month', ${{i}}, 'Nati a ${{m}}')" style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;"><div style="width:100px;">${{m}}</div><div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;"><div style="height:100%;width:${{w}}%;background:var(--primary);border-radius:6px;"></div></div><div style="font-weight:bold;">${{mCount[i]}}</div></div>`;
            }}).join('');
            const tSets = {{ 'Compleanno': new Set(), 'Onomastico': new Set(), 'Anniversario': new Set() }};
            events.forEach(e => {{ const k = e.Cognome + '|' + e.Nome; if (tSets[e.tipoDisplay]) tSets[e.tipoDisplay].add(k); else tSets['Anniversario'].add(k); }});
            const tCount = {{}}; for(let key in tSets) tCount[key] = tSets[key].size;
            const maxT = Math.max(...Object.values(tCount)) || 1;
            document.getElementById('stats-types').innerHTML = Object.entries(tCount).map(([k, v]) => {{
                if (v === 0) return ''; const w = (v/maxT)*100;
                return `<div class="clickable-stat" onclick="openStatsModal('type', '${{k}}', '${{k}}')" style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;"><div style="width:100px;">${{k}}</div><div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;"><div style="height:100%;width:${{w}}%;background:#ec4899;border-radius:6px;"></div></div><div style="font-weight:bold;">${{v}}</div></div>`;
            }}).join('');
            const gSets = {{ 'M': new Set(), 'F': new Set() }};
            events.forEach(e => {{ const k = e.Cognome + '|' + e.Nome; let g = e.Genere ? e.Genere.toUpperCase().trim() : 'M'; if (!gSets[g]) g = 'M'; gSets[g].add(k); }});
            const peopleGender = {{ 'M': gSets['M'].size, 'F': gSets['F'].size }};
            const maxG = Math.max(peopleGender['M'], peopleGender['F']) || 1;
            document.getElementById('stats-gender').innerHTML = [{{ label: 'Maschile', code: 'M', count: peopleGender['M'], color: 'var(--primary)' }}, {{ label: 'Femminile', code: 'F', count: peopleGender['F'], color: '#ec4899' }}].map(item => {{
                if (item.count === 0) return ''; const w = (item.count / maxG) * 100;
                return `<div class="clickable-stat" onclick="openStatsModal('gender', '${{item.code}}', 'Genere ${{item.label}}')" style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;"><div style="width:100px;">${{item.label}}</div><div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;"><div style="height:100%;width:${{w}}%;background:${{item.color}};border-radius:6px;"></div></div><div style="font-weight:bold;">${{item.count}}</div></div>`;
            }}).join('');
            const grSets = {{ 'Amici': new Set(), 'Mazzarisi': new Set(), 'Pricci': new Set(), 'Famiglia': new Set(), 'Geometri': new Set(), 'Febbre del sabato': new Set() }};
            const groupCodes = {{ 'Amici': 'A', 'Mazzarisi': 'M', 'Pricci': 'P', 'Famiglia': 'F', 'Geometri': 'G', 'Febbre del sabato': 'S' }};
            events.forEach(e => {{
                const k = e.Cognome + '|' + e.Nome; const gStr = (e.Gruppo || '').toUpperCase();
                if (gStr.includes('A')) grSets['Amici'].add(k); if (gStr.includes('M')) grSets['Mazzarisi'].add(k);
                if (gStr.includes('P')) grSets['Pricci'].add(k); if (gStr.includes('F')) grSets['Famiglia'].add(k);
                if (gStr.includes('G')) grSets['Geometri'].add(k); if (gStr.includes('S')) grSets['Febbre del sabato'].add(k);
            }});
            const groupCounts = {{ 'Amici': grSets['Amici'].size, 'Mazzarisi': grSets['Mazzarisi'].size, 'Pricci': grSets['Pricci'].size, 'Famiglia': grSets['Famiglia'].size, 'Geometri': grSets['Geometri'].size, 'Febbre del sabato': grSets['Febbre del sabato'].size }};
            const maxG2 = Math.max(...Object.values(groupCounts)) || 1;
            const groupColors = {{ 'Amici': '#f59e0b', 'Mazzarisi': '#3b82f6', 'Pricci': '#10b981', 'Famiglia': '#8b5cf6', 'Geometri': '#06b6d4', 'Febbre del sabato': '#e11d48' }};
            document.getElementById('stats-groups').innerHTML = Object.entries(groupCounts).map(([label, count]) => {{
                 if (count === 0) return ''; const w = (count / maxG2) * 100; const color = groupColors[label] || 'var(--primary)'; const code = groupCodes[label];
                 return `<div class="clickable-stat" onclick="openStatsModal('group', '${{code}}', 'Gruppo ${{label}}')" style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;"><div style="width:100px;">${{label}}</div><div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;"><div style="height:100%;width:${{w}}%;background:${{color}};border-radius:6px;"></div></div><div style="font-weight:bold;">${{count}}</div></div>`;
            }}).join('');
        }}
        
        // --- PDF GENERATORS (RESTORED FULL VERSION) ---
        function addFooter(doc) {{
            const totalPages = doc.internal.getNumberOfPages();
            const groupsText = getSelectedGroupNames();
            doc.setFontSize(10); 
            doc.setFont("helvetica", "normal");
            doc.setTextColor(100, 100, 100);
            
            for (let i = 1; i <= totalPages; i++) {{
                doc.setPage(i);
                const footerText = `${{groupsText}} (pag. ${{i}}/${{totalPages}})`;
                doc.text(footerText, doc.internal.pageSize.width / 2, doc.internal.pageSize.height - 10, {{ align: "center" }});
            }}
        }}

        function generateSiriPDF() {{
            closePrintModal();
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF({{ orientation: 'portrait', unit: 'mm', format: 'a4' }});
            
            // Titolo
            doc.setFont("helvetica", "bold");
            doc.setFontSize(20);
            doc.setTextColor(0,0,0);
            doc.text("Testo per Siri", 105, 20, {{ align: "center" }});
            
            doc.setFontSize(10);
            doc.setFont("helvetica", "normal");
            doc.text("Fonte: " + TXT_URL_SOURCE, 105, 30, {{ align: "center" }});

            // ORA USIAMO DIRETTAMENTE IL TESTO INIETTATO DA PYTHON
            doc.setFont("helvetica", "normal");
            doc.setFontSize(16);
            doc.setTextColor(0,0,0);
            
            const splitText = doc.splitTextToSize(SIRI_TEXT, 180); 
            doc.text(splitText, 15, 45);
            
            window.open(doc.output('bloburl'), '_blank');
        }}

        function generateRubricaPDF() {{
            closePrintModal();
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF({{ orientation: 'portrait', unit: 'mm', format: 'a4' }});
            const pageWidth = doc.internal.pageSize.width;
            const pageHeight = doc.internal.pageSize.height;
            const marginX = 12; const marginY = 15; const colGap = 10;
            const colWidth = (pageWidth - (marginX * 2) - colGap) / 2;
            const nameWidth = 43; 
            
            let cursorY = 15; let currentColumn = 0; let countInColumn = 0; 
            
            const people = getGroupedPeople();
            const sortedList = Object.values(people).sort((a, b) => {{ if (a.c !== b.c) return a.c.localeCompare(b.c); return a.n.localeCompare(b.n); }});
            
            let totalEvents = 0;
            sortedList.forEach(p => totalEvents += p.i.length);

            doc.setFont("helvetica", "bold"); doc.setFontSize(16);
            doc.text(`Festività parenti e amici (${{totalEvents}})`, pageWidth / 2, cursorY, {{ align: "center" }});
            cursorY += 8; const listStartY = cursorY; 
            
            doc.setFontSize(9);
            const rowHeight = 5; const boxPaddingTop = 4; const boxPaddingBottom = 1; 
            let boxStartY = cursorY - boxPaddingTop; 

            sortedList.forEach((p, index) => {{
                let bDayStr = ''; let nameDayStr = ''; let annivStr = '';
                p.i.forEach(i => {{
                    const d = String(i.pDate.day).padStart(2, '0');
                    const m = String(i.pDate.month).padStart(2, '0');
                    const fullY = i.pDate.year ? i.pDate.year : '';
                    const shortY = fullY ? fullY.slice(-2) : '';
                    if (i.tipoDisplay === 'Compleanno') {{ bDayStr = shortY ? `(${{d}}/${{m}}/${{shortY}})` : `(${{d}}/${{m}})`; }} 
                    else if (i.tipoDisplay === 'Anniversario') {{ annivStr = shortY ? `(${{d}}/${{m}}/${{shortY}})` : `(${{d}}/${{m}})`; }} 
                    else if (i.tipoDisplay === 'Onomastico') {{ nameDayStr = `[${{d}}-${{m}}]`; }}
                }});
                const datesArr = [];
                if (bDayStr) datesArr.push(bDayStr); if (nameDayStr) datesArr.push(nameDayStr); if (annivStr) datesArr.push(annivStr);
                const datesText = datesArr.join('   '); 

                if (cursorY > pageHeight - marginY - 15) {{ 
                    if (countInColumn % 10 !== 0) {{
                        const xBaseOld = marginX + (currentColumn * (colWidth + colGap));
                        let boxBottom = cursorY - rowHeight + boxPaddingBottom;
                        doc.setDrawColor(180, 180, 180); doc.setLineWidth(0.1);
                        doc.rect(xBaseOld - 1, boxStartY, colWidth + 2, boxBottom - boxStartY);
                        doc.setDrawColor(0);
                    }}
                    if (currentColumn === 0) {{ currentColumn = 1; cursorY = listStartY; }} 
                    else {{ doc.addPage(); currentColumn = 0; cursorY = 15; }}
                    boxStartY = cursorY - boxPaddingTop;
                }}
                
                const xBase = marginX + (currentColumn * (colWidth + colGap));
                const xDate = xBase + nameWidth; 
                doc.setFont("helvetica", "normal");
                const nameStr = `${{p.c}} ${{p.n}}`;
                doc.text(nameStr, xBase, cursorY);
                const textWidth = doc.getTextWidth(nameStr);
                const lineStart = xBase + textWidth + 1; const lineEnd = xDate - 1; 
                if (lineEnd > lineStart) {{ doc.setDrawColor(180, 180, 180); doc.setLineWidth(0.1); doc.setLineDash([0.5, 0.5], 0); doc.line(lineStart, cursorY, lineEnd, cursorY); doc.setDrawColor(0); doc.setLineDash([]); }}
                doc.text(datesText, xDate, cursorY);
                cursorY += rowHeight; countInColumn++;
                if (countInColumn > 0 && (countInColumn % 10 === 0 || index === sortedList.length - 1)) {{
                    let boxBottom = cursorY - rowHeight + boxPaddingBottom;
                    let h = boxBottom - boxStartY;
                    doc.setDrawColor(180, 180, 180); doc.setLineWidth(0.1);
                    doc.rect(xBase - 1, boxStartY, colWidth + 2, h); doc.setDrawColor(0);
                    cursorY += 3; boxStartY = cursorY - boxPaddingTop;
                }}
            }});
            
            addFooter(doc);
            window.open(doc.output('bloburl'), '_blank');
        }}

        function generateCalendarMaxPDF() {{
            closePrintModal();
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF({{ orientation: 'portrait', unit: 'mm', format: 'a4' }});
            
            // USA ANNO DALLA DATA DI RIFERIMENTO GLOBALE
            const year = REF_DATE.getFullYear();
            
            const pageWidth = doc.internal.pageSize.width;
            const pageHeight = doc.internal.pageSize.height;
            const margin = 20; const colGap = 10;
            const colWidth = (pageWidth - (margin * 2) - colGap) / 2;
            
            for (let m = 0; m < 12; m++) {{
                if (m > 0) doc.addPage();
                
                const monthlyEvents = events.filter(e => e.pDate.month === (m + 1));
                
                doc.setFont("helvetica", "bold"); doc.setFontSize(20); doc.setTextColor(0,0,0);
                doc.text(`${{months[m]}} ${{year}} (${{monthlyEvents.length}})`, pageWidth/2, 15, {{align: "center"}});
                
                const eventsByDay = {{}};
                monthlyEvents.forEach(e => {{ if (!eventsByDay[e.pDate.day]) eventsByDay[e.pDate.day] = []; eventsByDay[e.pDate.day].push(e); }});
                const sortedDays = Object.keys(eventsByDay).map(Number).sort((a,b) => a-b);
                
                let cursorY = 25; let col = 0; let startY = cursorY;
                sortedDays.forEach(day => {{
                    const dayEvents = eventsByDay[day];
                    const mergedList = processDayEvents(dayEvents); 
                    let totalBoxHeight = 0; const itemSpacing = 2; 
                    mergedList.forEach((item, idx) => {{
                        const h = item.isMerged ? 16 : 11;
                        totalBoxHeight += h;
                        if (idx < mergedList.length - 1) totalBoxHeight += itemSpacing;
                    }});
                    totalBoxHeight += 6; 
                    if (cursorY + totalBoxHeight > pageHeight - margin - 15) {{ 
                        if (col === 0) {{ col = 1; cursorY = startY; }} 
                        else {{ doc.addPage(); doc.text(`${{months[m]}} ${{year}} (cont.)`, pageWidth/2, 15, {{align: "center"}}); col = 0; cursorY = 25; startY = 25; }}
                    }}
                    const xBase = margin + (col * (colWidth + colGap));
                    doc.setFillColor(230, 230, 230); doc.rect(xBase + 1, cursorY + 1, colWidth, totalBoxHeight, 'F'); 
                    doc.setFillColor(255, 255, 255); doc.setDrawColor(200, 200, 200); doc.rect(xBase, cursorY, colWidth, totalBoxHeight, 'FD'); doc.setDrawColor(0);
                    const dateBoxWidth = 14; const dayCenterY = cursorY + (totalBoxHeight / 2);
                    const eventDateObj = new Date(year, m, day);
                    const dayName = eventDateObj.toLocaleDateString('it-IT', {{ weekday: 'short' }}).toUpperCase().substring(0,3);
                    
                    doc.setFontSize(8); doc.setFont("helvetica", "normal"); doc.setTextColor(100, 100, 100);
                    doc.text(dayName, xBase + (dateBoxWidth/2), dayCenterY - 3, {{align: "center"}});
                    doc.setFontSize(14); doc.setFont("helvetica", "bold"); doc.setTextColor(0, 0, 0); 
                    doc.text(String(day), xBase + (dateBoxWidth/2), dayCenterY + 3, {{align: "center"}});
                    doc.setDrawColor(220, 220, 220); doc.line(xBase + dateBoxWidth, cursorY + 2, xBase + dateBoxWidth, cursorY + totalBoxHeight - 2);
                    
                    let currentTextY = cursorY + 3; const textX = xBase + dateBoxWidth + 3;
                    mergedList.forEach(item => {{
                        if (item.type === 'Compleanno') doc.setTextColor(0, 51, 102); 
                        else if (item.type === 'Onomastico') doc.setTextColor(0, 100, 0); 
                        else if (item.type === 'Anniversario') doc.setTextColor(153, 0, 51); 
                        else doc.setTextColor(0,0,0);
                        doc.setFontSize(10); doc.setFont("helvetica", "bold");
                        if (item.isMerged) {{
                            doc.text(item.l1, textX, currentTextY + 4);
                            doc.text(item.l2, textX, currentTextY + 8.5); 
                            doc.setTextColor(80, 80, 80);
                            drawLabelWithBoldNumber(doc, item.lbl, textX, currentTextY + 13);
                            currentTextY += 16 + itemSpacing;
                        }} else {{
                            doc.text(item.l1, textX, currentTextY + 4);
                            doc.setTextColor(80, 80, 80);
                            drawLabelWithBoldNumber(doc, item.lbl, textX, currentTextY + 8.5);
                            currentTextY += 11 + itemSpacing;
                        }}
                    }});
                    cursorY += totalBoxHeight + 3; 
                }});
            }}
            addFooter(doc);
            window.open(doc.output('bloburl'), '_blank');
        }}

        function generateCalendarMinPDF() {{
            closePrintModal();
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF({{ orientation: 'portrait', unit: 'mm', format: 'a4' }});
            
            // USA ANNO DALLA DATA DI RIFERIMENTO GLOBALE
            const year = REF_DATE.getFullYear();
            
            const pageWidth = doc.internal.pageSize.width;
            const pageHeight = doc.internal.pageSize.height;
            const margin = 10; 
            const colGap = 4; 
            const colWidth = (pageWidth - (margin * 2) - (colGap * 2)) / 3;
            
            const printQueue = [];
            let totalYearEvents = 0;
            
            for (let m = 0; m < 12; m++) {{
                const monthlyEvents = events.filter(e => e.pDate.month === (m + 1));
                if (monthlyEvents.length > 0) {{
                    totalYearEvents += monthlyEvents.length;
                    printQueue.push({{ type: 'header', text: `${{months[m]}} (${{monthlyEvents.length}})`, height: 10 }});
                    const eventsByDay = {{}};
                    monthlyEvents.forEach(e => {{ if (!eventsByDay[e.pDate.day]) eventsByDay[e.pDate.day] = []; eventsByDay[e.pDate.day].push(e); }});
                    const sortedDays = Object.keys(eventsByDay).map(Number).sort((a,b) => a-b);
                    sortedDays.forEach(day => {{
                        const dayEvents = eventsByDay[day];
                        const mergedList = processDayEvents(dayEvents);
                        let totalBoxHeight = 0; const itemSpacing = 0.5; 
                        mergedList.forEach((item, idx) => {{ 
                            const h = item.isMerged ? 11 : 7; 
                            totalBoxHeight += h; 
                            if (idx < mergedList.length - 1) totalBoxHeight += itemSpacing; 
                        }});
                        totalBoxHeight += 3; 
                        printQueue.push({{ type: 'dayBox', day: day, mIndex: m, mergedList: mergedList, height: totalBoxHeight }});
                    }});
                }}
            }}

            let cursorY = 15;
            let currentColumn = 0; 
            
            doc.setFont("helvetica", "bold"); 
            doc.setFontSize(16); 
            doc.text(`Calendario ${{year}} (${{totalYearEvents}})`, pageWidth/2, cursorY, {{align: "center"}});
            cursorY += 10;
            const startY = cursorY; 

            const col1X = margin;
            const col2X = margin + colWidth + colGap;
            const col3X = margin + (colWidth + colGap) * 2;

            for (let i = 0; i < printQueue.length; i++) {{
                const item = printQueue[i];
                let checkHeight = item.height;

                if (item.type === 'header' && i + 1 < printQueue.length) {{
                    const nextItem = printQueue[i+1];
                    if (nextItem.type === 'dayBox') {{
                        checkHeight += nextItem.height; 
                    }}
                }}

                if (cursorY + checkHeight > pageHeight - margin - 15) {{ 
                    currentColumn++;
                    cursorY = startY; 
                    if (currentColumn > 2) {{
                        doc.addPage();
                        currentColumn = 0;
                        cursorY = 15; 
                    }}
                }}

                let currentX = col1X;
                if (currentColumn === 1) currentX = col2X;
                if (currentColumn === 2) currentX = col3X;

                if (item.type === 'header') {{
                    doc.setFont("helvetica", "bold");
                    doc.setFontSize(12);
                    doc.setTextColor(0,0,0);
                    doc.text(item.text.toUpperCase(), currentX + (colWidth/2), cursorY + 6, {{align: "center"}});
                    doc.setDrawColor(0);
                    doc.setLineWidth(0.3);
                    doc.line(currentX, cursorY + 8, currentX + colWidth, cursorY + 8);
                }} 
                else if (item.type === 'dayBox') {{
                    doc.setDrawColor(180, 180, 180);
                    doc.setLineWidth(0.1);
                    doc.rect(currentX, cursorY, colWidth, item.height); 
                    
                    const dateBoxWidth = 10;
                    const dayCenterY = cursorY + (item.height / 2);
                    const eventDateObj = new Date(year, item.mIndex, item.day);
                    const dayName = eventDateObj.toLocaleDateString('it-IT', {{ weekday: 'short' }}).toUpperCase().substring(0,3);

                    doc.setTextColor(37, 99, 235); 
                    doc.setFontSize(10); doc.setFont("helvetica", "bold");
                    doc.text(String(item.day), currentX + (dateBoxWidth/2), dayCenterY, {{align: "center"}});
                    
                    doc.setTextColor(150, 150, 150);
                    doc.setFontSize(6); 
                    doc.text(dayName, currentX + (dateBoxWidth/2), dayCenterY + 3, {{align: "center"}});

                    doc.setDrawColor(220, 220, 220);
                    doc.setLineWidth(0.1);
                    doc.line(currentX + dateBoxWidth, cursorY + 2, currentX + dateBoxWidth, cursorY + item.height - 2);

                    let txtY = cursorY + 1.5;
                    const txtX = currentX + dateBoxWidth + 2;
                    const itemSpacing = 0.5;

                    item.mergedList.forEach(ev => {{
                        if (ev.type === 'Compleanno') doc.setTextColor(0, 51, 102); 
                        else if (ev.type === 'Onomastico') doc.setTextColor(0, 100, 0); 
                        else if (ev.type === 'Anniversario') doc.setTextColor(153, 0, 51); 
                        else doc.setTextColor(0,0,0);
                        doc.setFontSize(8); 
                        doc.setFont("helvetica", "bold");
                        if (ev.isMerged) {{
                            doc.text(ev.l1, txtX, txtY + 3);
                            doc.text(ev.l2, txtX, txtY + 6);
                            doc.setTextColor(80, 80, 80);
                            drawLabelWithBoldNumber(doc, ev.lbl, txtX, txtY + 8.5);
                            txtY += 11 + itemSpacing;
                        }} else {{
                            doc.text(ev.l1, txtX, txtY + 3);
                            doc.setTextColor(80, 80, 80);
                            drawLabelWithBoldNumber(doc, ev.lbl, txtX, txtY + 6);
                            txtY += 7 + itemSpacing;
                        }}
                    }});
                }}
                cursorY += item.height + 2; 
            }}
            addFooter(doc);
            window.open(doc.output('bloburl'), '_blank');
        }}
        
        function drawLabelWithBoldNumber(doc, text, x, y) {{
            const regex = /(.*)(\\(\\d+\\))(.*)/; 
            const match = text.match(regex);
            doc.setFontSize(8); 
            if (match) {{
                const prefix = match[1];
                const numberPart = match[2]; 
                doc.setFont("helvetica", "normal");
                doc.text(prefix, x, y);
                const w1 = doc.getTextWidth(prefix);
                doc.setFont("helvetica", "bold");
                doc.setTextColor(0,0,0); 
                doc.text(numberPart, x + w1, y);
            }} else {{
                doc.setFont("helvetica", "normal");
                doc.text(text, x, y);
            }}
        }}

        function switchTab(tabId) {{
            // 1. SALVIAMO LO SCROLL DELLA TAB CORRENTE (PRIMA DI USCIRE)
            tabScrollPositions[activeTabId] = window.scrollY;

            // 2. CAMBIAMO TAB
            activeTabId = tabId; 
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            document.querySelector(`button[onclick="switchTab('${{tabId}}')"]`).classList.add('active');
            
            const appContainer = document.getElementById('app-container');
            if (tabId === 'home' || tabId === 'stats') {{ appContainer.classList.add('bg-yellow-mode'); }} 
            else {{ appContainer.classList.remove('bg-yellow-mode'); }}
            
            // 3. LOGICA DI RIPRISTINO SCROLL
            if (tabId === 'home' && isFirstHomeLoad) {{
                // Caso Speciale: PRIMA VOLTA CHE APRO LA HOME -> Vado su "Oggi"
                setTimeout(() => {{
                    const el = document.getElementById('focus-target');
                    if (el) {{ el.scrollIntoView({{behavior: "smooth", block: "center"}}); }}
                }}, 50);
                isFirstHomeLoad = false; // Disabilito per le prossime volte
            }} else {{
                // Caso Standard: RIPRISTINO POSIZIONE SALVATA
                setTimeout(() => {{
                    window.scrollTo({{ top: tabScrollPositions[tabId], behavior: "auto" }});
                }}, 0);
            }}
        }}

        let touchStartY = 0; let touchEndY = 0;
        const indicator = document.getElementById('refresh-indicator');
        
        // --- FUNZIONE PER FORZARE IL RICARICAMENTO DAL SERVER ---
        function forceReload() {{
            const url = new URL(window.location.href);
            url.searchParams.set('t', new Date().getTime()); // Aggiunge timestamp unico
            window.location.href = url.toString();
        }}

        document.addEventListener('touchstart', e => {{ touchStartY = e.touches[0].clientY; }}, {{passive: true}});
        document.addEventListener('touchmove', e => {{ touchEndY = e.touches[0].clientY; if (window.scrollY === 0 && touchEndY > touchStartY + 50) {{ indicator.classList.add('show'); }} }}, {{passive: true}});
        
        document.addEventListener('touchend', e => {{ 
            indicator.classList.remove('show'); 
            // Se l'utente trascina verso il basso (Pull-to-refresh)
            if (window.scrollY === 0 && touchEndY > touchStartY + 150) {{ 
                forceReload(); // Chiamiamo la funzione che bypassa la cache
            }} 
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            calculateEvents(); renderHome(); renderRubrica(); renderStats();
            document.getElementById('app-container').classList.add('bg-yellow-mode');
            
            // Trigger iniziale per posizionare la Home su Oggi
            switchTab('home'); 
        }});

    </script>
</body>
</html>"""
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"🎉 Successo! File generato: {OUTPUT_FILE}")

if __name__ == "__main__":
    target_date = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        try:
            target_date = datetime.strptime(arg, "%d-%m-%Y")
            print(f"🕒 MODALITÀ VIAGGIO NEL TEMPO ATTIVA: {target_date.strftime('%d/%m/%Y')}")
        except ValueError:
            print("⚠️ Formato data non valido (Usa GG-MM-AAAA). Uso data odierna.")
    
    dati_csv = leggi_e_processa_dati(INPUT_FILE)
    if dati_csv:
        genera_txt_siri_discorsivo(dati_csv, target_date)
        genera_html(dati_csv, target_date)
        
        # Carica su GitHub
        aggiorna_github()

        print("--------------------------------------------------")
        print("✅ Elaborazione completata e file caricati su GitHub.")
        
        # Aspetta l'input dell'utente prima di aprire il file
        input("⌨️  Premi INVIO per aprire il calendario nel browser e terminare...")

        try:
            file_path = os.path.abspath(OUTPUT_FILE)
            webbrowser.open(f'file://{file_path}')
            print(f"🚀 Apertura file nel browser...")
        except Exception as e:
            print(f"⚠️ Impossibile aprire il browser automaticamente: {e}")