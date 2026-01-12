import csv
import json
import os
import sys
import webbrowser
from datetime import datetime
from itertools import groupby

# Nome: Feste.py
# Data ultima modifica: 12/01/2026
# Descrizione: Versione DEFINITIVA OTTIMIZZATA PER SIRI + COPPIE + COLORI.
#              - "Tra n gg" diventato "- n".
#              - Nomi colorati (Blu Compleanni, Verde Onomastici, Porpora Anniversari).
#              - Anniversari accorpati in Feste.txt ("Tizio e Caio").
#              - Time Travel (parametro data).
#              - HTML completo.
# File di input: Feste-elenco.csv
# File di output: Feste.html, Feste.txt

# Configurazione dei file
INPUT_FILE = 'Feste-elenco.csv'
BACKUP_FILE = 'Feste-backup.csv'
OUTPUT_FILE = 'Feste.html'
OUTPUT_TXT = 'Feste.txt'

ICON_URL = "https://sebastiano-mazzarisi.github.io/Test/Feste.png?v=11"

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
    """
    Funzione helper per trasformare una lista di eventi (dello stesso giorno)
    in una lista di frasi, accorpando gli anniversari.
    """
    lines = []
    skip_indices = set()
    
    for i, e in enumerate(gruppo_eventi):
        if i in skip_indices:
            continue
            
        phrase = ""
        
        # Logica Accorpamento Anniversari
        if e['Tipo'] == 'Anniversario':
            match_index = -1
            # Cerca un partner nello stesso gruppo (stessi anni)
            for j in range(i + 1, len(gruppo_eventi)):
                other = gruppo_eventi[j]
                if j not in skip_indices and other['Tipo'] == 'Anniversario' and other['Years'] == e['Years']:
                    match_index = j
                    break
            
            if match_index != -1:
                # Trovato accoppiamento!
                partner = gruppo_eventi[match_index]
                skip_indices.add(match_index)
                
                # Ordine alfabetico per nome nella frase
                nomi = sorted([f"{e['Nome']} {e['Cognome']}", f"{partner['Nome']} {partner['Cognome']}"])
                phrase = f"Anniversario di {nomi[0]} e {nomi[1]}"
                if e['Years']:
                    phrase += f" ({e['Years']} anni)"
            else:
                # Anniversario singolo
                phrase = f"Anniversario di {e['Nome']} {e['Cognome']}"
                if e['Years']:
                    phrase += f" ({e['Years']} anni)"
        
        # Logica Compleanni / Onomastici
        elif e['Tipo'] == 'Compleanno':
            phrase = f"{e['Nome']} {e['Cognome']} festeggia il compleanno"
            if e['Years']: phrase += f" e compie {e['Years']} anni"
            
        elif e['Tipo'] == 'Onomastico':
            phrase = f"È l'onomastico di {e['Nome']} {e['Cognome']}"
            
        phrase += "."
        lines.append(phrase)
        
    return lines

def genera_txt_siri_discorsivo(dati, fake_today=None):
    """
    Genera Feste.txt raggruppando date e unendo le coppie di anniversari.
    Nota: Per Siri manteniamo un linguaggio naturale ("Tra X giorni"), 
    la modifica "- X" è applicata alla parte visiva (HTML/PDF).
    """
    if fake_today:
        today = fake_today.replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"🗣️ Generazione Siri simulando data: {today.strftime('%d/%m/%Y')}")
    else:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        print("🗣️ Generazione Siri con data odierna reale.")

    mesi_nomi = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", 
                 "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    
    processed_events = []

    for item in dati:
        try:
            parts = item.get('Data', '').split('/')
            if len(parts) < 2: continue
            
            day, month = int(parts[0]), int(parts[1])
            year_str = parts[2] if len(parts) > 2 and parts[2] else None
            
            try:
                next_event = datetime(today.year, month, day)
            except ValueError:
                continue 
            
            if next_event < today:
                next_event = next_event.replace(year=today.year + 1)
            
            days_until = (next_event - today).days
            
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
                'MonthName': mesi_nomi[month]
            })
        except:
            continue

    processed_events.sort(key=lambda x: x['DaysUntil'])

    lines = []
    if fake_today:
        lines.append(f"Riepilogo feste (Simulazione al {today.strftime('%d/%m/%Y')}).\n")
    else:
        lines.append("Ecco il riepilogo delle feste.\n")

    # --- OGGI ---
    events_today = [e for e in processed_events if e['DaysUntil'] == 0]
    if events_today:
        lines.append("Attenzione, oggi c'è una festa!")
        today_date_str = f"Oggi, {events_today[0]['Day']} {events_today[0]['MonthName']},"
        lines.append(today_date_str)
        
        frasi_oggi = formatta_eventi_gruppo(events_today)
        lines.extend(frasi_oggi)
    else:
        lines.append("Oggi, nessun evento in programma.")

    lines.append("\n") 

    # --- PROSSIMI ---
    upcoming = [e for e in processed_events if e['DaysUntil'] > 0][:8] 
    
    if upcoming:
        lines.append("Nei prossimi giorni:")
        
        groups = []
        for k, g in groupby(upcoming, key=lambda x: x['DaysUntil']):
            groups.append(list(g))
            
        for i, group in enumerate(groups):
            first = group[0]
            
            if i == 1:
                lines.append("\nE ancora:")
            elif i > 1:
                lines.append("") 
            
            if first['DaysUntil'] == 1:
                header = f"Domani, il {first['Day']} {first['MonthName']},"
            else:
                header = f"Tra {first['DaysUntil']} giorni, il {first['Day']} {first['MonthName']},"
            
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
    
    if fake_today:
        js_date_code = f"new Date({fake_today.year}, {fake_today.month - 1}, {fake_today.day})"
        print(f"🌐 Generazione HTML con data fissa: {fake_today.strftime('%d/%m/%Y')}")
    else:
        js_date_code = "new Date()"
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
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
            
            --past-event-bg: rgba(16, 185, 129, 0.08); 
            --past-event-text: #059669;
            --today-bg: #fef2f2;
            --today-border: #ef4444;
            --border-color: #cbd5e1;

            /* Nuovi colori richiesti */
            --color-compleanno: #003366; /* Blu scuro */
            --color-onomastico: #006400; /* Verde scuro */
            --color-anniversario: #990033; /* Rosso porpora / Cremisi */
        }}
        
        html {{ font-size: 16px; }} 

        @media (min-width: 768px) {{
            html {{ font-size: 20px; }}
        }}

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

        .app-container.bg-yellow-mode {{
            background-color: var(--bg-yellowish) !important;
        }}

        /* --- HEADER --- */
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
        
        .header-content {{
            position: relative;
            max-width: 100%;
        }}
        
        .header h1 {{ 
            font-size: 1.6rem; 
            font-weight: 800; 
            margin: 0;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .header p {{ 
            font-size: 0.95rem; 
            opacity: 0.9; 
            margin-top: 5px; 
            font-weight: 400;
        }}
        
        /* Bottone Stampante */
        .print-btn {{
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            background: white; 
            border: none;
            color: var(--primary); 
            font-size: 1.5rem;
            cursor: pointer;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s, transform 0.2s;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        .print-btn:hover {{ background: #f8fafc; transform: translateY(-50%) scale(1.05); }}

        /* --- TABS --- */
        .tab-content {{ 
            display: none; 
            padding: 1rem;
            animation: fadeIn 0.3s ease;
        }}
        .tab-content.active {{ display: block; }}
        
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 3px 6px rgba(0,0,0,0.05);
            transition: background-color 0.3s;
        }}

        .is-past {{
            background-color: var(--past-event-bg) !important;
        }}
        .is-past .cal-date {{ opacity: 0.7; }} 
        .is-past .cal-name {{ opacity: 0.9; }}
        
        .rubrica-row.is-past-row .rubrica-type, 
        .rubrica-row.is-past-row .rubrica-date {{
            opacity: 0.6;
        }}

        .is-today {{
            background-color: var(--today-bg) !important;
            border-left-color: var(--today-border) !important;
        }}
        .is-today .days-label {{ color: var(--today-border) !important; font-weight: 900; }}

        /* --- CALENDARIO --- */
        .calendar-item {{
            display: flex;
            align-items: center;
            padding: 14px; 
            background: white;
            border-bottom: 1px solid var(--border-color);
        }}
        .calendar-item:last-child {{ border-bottom: none; }}
        
        .cal-date {{
            width: 60px;
            text-align: center;
            font-weight: 800;
            font-size: 1.3rem; 
            color: var(--primary);
            line-height: 1.1;
            margin-right: 15px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .cal-date small {{ display: block; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); margin-top: 2px; }}
        
        .cal-info {{ flex: 1; }}
        
        .event-row {{
            margin-bottom: 12px;
            position: relative; 
        }}
        .event-row:last-child {{ margin-bottom: 0; }}
        
        .cal-name {{ 
            font-weight: 700; 
            font-size: 1.1rem; 
            margin-bottom: 2px; 
            line-height: 1.2; 
            padding-right: 60px; 
        }}

        /* Classi specifiche per colore nome */
        .name-compleanno {{ color: var(--color-compleanno); }}
        .name-onomastico {{ color: var(--color-onomastico); }}
        .name-anniversario {{ color: var(--color-anniversario); }}

        .cal-type {{ font-size: 0.9rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }}

        .home-badge {{
            position: absolute;
            top: 0;
            right: 0;
            background: var(--primary-light);
            color: var(--primary);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .bold-number {{ font-weight: 900; color: var(--text-main); }}

        .month-header {{
            background: #f1f5f9;
            color: var(--text-main);
            padding: 10px 16px;
            font-size: 1rem;
            font-weight: 800;
            text-transform: uppercase;
            position: sticky;
            top: 90px;
            z-index: 40;
            border-bottom: 1px solid var(--border-color);
            border-top: 1px solid var(--border-color);
        }}

        @media (min-width: 768px) {{
            .month-header {{ top: 100px; }}
        }}

        /* --- RICERCA AVANZATA --- */
        .search-wrapper {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 1rem; 
        }}

        .search-container {{
            position: relative;
            flex-grow: 1; 
        }}

        .search-box {{
            width: 100%;
            padding: 12px 40px 12px 14px; 
            border: 2px solid var(--border-color);
            border-radius: 12px;
            font-size: 1.1rem; 
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-box:focus {{ border-color: var(--primary); }}

        .search-clear {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            background: #e2e8f0;
            border: none;
            color: #64748b;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            display: none; 
            align-items: center;
            justify-content: center;
            padding-bottom: 2px;
        }}
        
        .result-count {{
            background: var(--primary);
            color: white;
            min-width: 50px;
            height: 50px;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.4rem;
            line-height: 1;
            flex-shrink: 0;
            box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
        }}

        /* --- RUBRICA COMPATTA --- */
        .rubrica-item {{
            background: white;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 12px;
            padding: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}
        
        .rubrica-name {{ 
            font-weight: 800; 
            font-size: 1.15rem; 
            color: var(--text-main); 
            margin-bottom: 6px;
            border-bottom: 1px solid #f1f5f9;
            padding-bottom: 4px;
        }}
        
        .rubrica-row {{
            display: flex;
            align-items: center;
            padding: 4px 2px;
            font-size: 0.95rem;
        }}
        
        .rubrica-type {{ 
            flex: 1; 
            color: var(--text-muted); 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            font-weight: 500;
        }}
        
        .rubrica-date {{ 
            font-weight: 600; 
            color: var(--text-main); 
            font-size: 0.9rem;
            min-width: 80px;
            text-align: right;
        }}

        /* --- NAVBAR --- */
        .nav-bar {{
            position: fixed;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 600px;
            background: white;
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            border-top: 1px solid var(--border-color);
            z-index: 100;
            padding-bottom: max(10px, env(safe-area-inset-bottom));
            box-shadow: 0 -4px 20px rgba(0,0,0,0.05);
        }}

        .nav-item {{
            border: none;
            background: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            color: var(--text-muted);
            font-size: 0.75rem; 
            font-weight: 600;
            cursor: pointer;
            width: 25%;
        }}

        .nav-item.active {{ color: var(--primary); }}
        .nav-item svg {{ width: 24px; height: 24px; stroke-width: 2.5px; }}

        /* --- UTILITY --- */
        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; margin-left: auto; }}
        
        #refresh-indicator {{
            position: fixed;
            top: 70px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.8rem;
            z-index: 200;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
        }}
        #refresh-indicator.show {{ opacity: 1; }}

    </style>
</head>
<body>
    
    <div id="refresh-indicator">Rilascia per aggiornare...</div>

    <div class="app-container" id="app-container">
        
        <div class="header">
            <div class="header-content">
                <h1>EVENTI E FESTE</h1>
                <p>Compleanni e Anniversari</p>
                <button class="print-btn" onclick="generatePDF()" title="Stampa PDF">
                    🖨️
                </button>
            </div>
        </div>

        <div id="tab-home" class="tab-content active">
            <h3 style="margin: 0.5rem 0 1rem; color: var(--text-muted); font-size: 1rem; text-transform: uppercase;">In Arrivo</h3>
            <div id="upcoming-list"></div>
        </div>

        <div id="tab-rubrica" class="tab-content">
            <div class="search-wrapper">
                <div class="search-container">
                    <input type="text" id="search-input" class="search-box" placeholder="Cerca..." oninput="filterRubrica()">
                    <button id="search-clear" class="search-clear" onclick="clearSearch()">✕</button>
                </div>
                <div class="result-count" id="search-counter">
                    <div id="count-val">0</div>
                </div>
            </div>
            <div id="rubrica-list"></div>
        </div>

        <div id="tab-calendario" class="tab-content" style="padding: 0;">
            <div id="calendar-list"></div>
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
        </div>

        <nav class="nav-bar">
            <button class="nav-item active" onclick="switchTab('home')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2 2H5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
                Home
            </button>
            <button class="nav-item" onclick="switchTab('rubrica')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                Rubrica
            </button>
            <button class="nav-item" onclick="switchTab('calendario')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                Cal
            </button>
            <button class="nav-item" onclick="switchTab('stats')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                Stats
            </button>
        </nav>

    </div>

    <script>
        const rawData = {json_dati};
        const months = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];
        const shortMonths = ['GEN', 'FEB', 'MAR', 'APR', 'MAG', 'GIU', 'LUG', 'AGO', 'SET', 'OTT', 'NOV', 'DIC'];
        let activeTabId = 'home'; // Tracking della scheda attiva

        function parseDate(dateStr) {{
            if (!dateStr) return null;
            const parts = dateStr.split('/');
            if (parts.length < 2) return null;
            return {{ day: parseInt(parts[0]), month: parseInt(parts[1]), year: parts[2] || null }};
        }}

        function getEventInfo(parsedDate) {{
            // INIETTO LA DATA FINTA O VERA QUI
            const today = {js_date_code};
            today.setHours(0,0,0,0);
            
            let eventDate = new Date(today.getFullYear(), parsedDate.month - 1, parsedDate.day);
            let isPast = false;
            
            if (eventDate < today) {{
                isPast = true;
                eventDate.setFullYear(today.getFullYear() + 1);
            }}
            
            const diffTime = eventDate - today;
            const daysUntil = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Verifico se era passato quest'anno rispetto alla data simulata
            const currentYearDate = new Date(today.getFullYear(), parsedDate.month - 1, parsedDate.day);
            const actuallyPastThisYear = currentYearDate.getTime() < today.getTime();

            return {{ daysUntil, actuallyPastThisYear }};
        }}

        let events = rawData.map(item => {{
            const pDate = parseDate(item.Data);
            if (!pDate) return null;
            const info = getEventInfo(pDate);
            let tipo = item.Festa;
            if (tipo !== 'Compleanno' && tipo !== 'Onomastico') tipo = 'Anniversario';
            
            let yearsTurning = null;
            if (pDate.year) {{
                const today = {js_date_code}; // Anche qui uso la data simulata per calcolo età
                const currentYear = today.getFullYear();
                yearsTurning = currentYear - parseInt(pDate.year);
            }}

            let currentAge = yearsTurning;

            return {{
                ...item,
                pDate,
                daysUntil: info.daysUntil,
                isPastThisYear: info.actuallyPastThisYear,
                tipoDisplay: tipo,
                yearsTurning: yearsTurning,
                currentAge: currentAge,
                Genere: item.Genere,
                Cognome: item.Cognome,
                Nome: item.Nome
            }};
        }}).filter(e => e !== null);

        // --- HELPER PER RAGGRUPPARE EVENTI DI UN GIORNO ---
        function processDayEvents(dayEvents) {{
            const mergedList = [];
            const skipIndices = new Set();
            
            for (let i = 0; i < dayEvents.length; i++) {{
                if (skipIndices.has(i)) continue;
                
                const e1 = dayEvents[i];
                let merged = null;
                
                // Logica Anniversari
                if (e1.tipoDisplay === 'Anniversario') {{
                    let matchIdx = -1;
                    for (let j = i + 1; j < dayEvents.length; j++) {{
                        if (skipIndices.has(j)) continue;
                        const e2 = dayEvents[j];
                        
                        if (e2.tipoDisplay === 'Anniversario' && e2.pDate.year === e1.pDate.year) {{
                            const g1 = e1.Genere ? e1.Genere.toUpperCase().trim() : '';
                            const g2 = e2.Genere ? e2.Genere.toUpperCase().trim() : '';
                            if (g1 !== g2) {{
                                matchIdx = j;
                                break;
                            }}
                        }}
                    }}
                    
                    if (matchIdx !== -1) {{
                        const e2 = dayEvents[matchIdx];
                        skipIndices.add(matchIdx);
                        
                        let fEvent = e1; 
                        let mEvent = e2;
                        if (e1.Genere && e1.Genere.toUpperCase().trim() === 'M') {{
                            fEvent = e2;
                            mEvent = e1;
                        }} 
                        
                        merged = {{
                            isMerged: true,
                            line1: `${{fEvent.Nome}} ${{fEvent.Cognome}}`,
                            line2: `${{mEvent.Nome}} ${{mEvent.Cognome}}`,
                            label: `Anniversario${{e1.yearsTurning !== null ? ' (' + e1.yearsTurning + ')' : ''}}`,
                            type: 'Anniversario',
                            // Per home badge
                            daysUntil: e1.daysUntil,
                            isPastThisYear: e1.isPastThisYear
                        }};
                    }}
                }}
                
                if (merged) {{
                    mergedList.push(merged);
                }} else {{
                    mergedList.push({{
                        isMerged: false,
                        line1: `${{e1.Nome}} ${{e1.Cognome}}`,
                        label: e1.tipoDisplay + (e1.yearsTurning !== null ? ` (${{e1.yearsTurning}})` : ''),
                        type: e1.tipoDisplay,
                        // Dati extra per render
                        daysUntil: e1.daysUntil,
                        isPastThisYear: e1.isPastThisYear
                    }});
                }}
            }}
            
            // Ordinamento: Compleanni > Anniversari > Onomastici
            const priority = {{ 'Compleanno': 1, 'Anniversario': 2, 'Onomastico': 3 }};
            mergedList.sort((a, b) => {{
                const pA = priority[a.type] || 99;
                const pB = priority[b.type] || 99;
                return pA - pB;
            }});
            
            return mergedList;
        }}
        
        // --- UTILS PER HTML ---
        function formatLabelHTML(label) {{
            // Trasforma "Testo (123)" in "Testo <span class='bold-number'>(123)</span>"
            return label.replace(/(\\(\\d+\\))/, '<span class="bold-number">$1</span>');
        }}

        function getColorClass(type) {{
            if (type === 'Compleanno') return 'name-compleanno';
            if (type === 'Onomastico') return 'name-onomastico';
            if (type === 'Anniversario') return 'name-anniversario';
            return '';
        }}

        // --- RENDER FUNCTIONS ---

        function renderHome() {{
            const container = document.getElementById('upcoming-list');
            const upcoming = events
                .filter(e => e.daysUntil >= 0 && e.daysUntil <= 45)
                .sort((a, b) => a.daysUntil - b.daysUntil);

            if (upcoming.length === 0) {{
                container.innerHTML = '<div style="text-align:center; padding:2rem; font-size:1rem; color:var(--text-muted)">Nessun evento imminente</div>';
                return;
            }}
            
            const groupedByDate = {{}};
            const uniqueDates = [];
            
            upcoming.forEach(e => {{
                const dateKey = `${{e.pDate.month}}-${{e.pDate.day}}`;
                if (!groupedByDate[dateKey]) {{
                    groupedByDate[dateKey] = [];
                    uniqueDates.push(e); 
                }}
                groupedByDate[dateKey].push(e);
            }});
            
            container.innerHTML = uniqueDates.map(refEvent => {{
                const dateKey = `${{refEvent.pDate.month}}-${{refEvent.pDate.day}}`;
                const dayEvents = groupedByDate[dateKey];
                const processed = processDayEvents(dayEvents);
                
                // MODIFICA RICHIESTA: "- N" invece di "Tra N gg"
                let dayLabel = `- ${{refEvent.daysUntil}}`;
                let cardClass = 'card';
                let borderStyle = 'border-left: 5px solid var(--primary);';
                
                if (refEvent.daysUntil === 0) {{
                    dayLabel = "OGGI!";
                    cardClass += ' is-today';
                }} else if (refEvent.daysUntil === 1) {{
                    dayLabel = "Domani";
                }}
                
                const badgeHtml = `<div class="home-badge">${{dayLabel}}</div>`;
                
                const eventsHtml = processed.map(item => {{
                    const icon = item.type === 'Compleanno' ? '🎂' : (item.type === 'Onomastico' ? '🌟' : '💍');
                    const labelHtml = formatLabelHTML(item.label);
                    const colorClass = getColorClass(item.type);
                    
                    if (item.isMerged) {{
                        return `
                        <div class="event-row">
                            <div class="cal-name ${{colorClass}}">${{item.line1}}</div>
                            <div class="cal-name ${{colorClass}}">${{item.line2}}</div>
                            <div class="cal-type">
                                <span>${{icon}} ${{labelHtml}}</span>
                            </div>
                        </div>`;
                    }} else {{
                        return `
                        <div class="event-row">
                            <div class="cal-name ${{colorClass}}">${{item.line1}}</div>
                            <div class="cal-type">
                                <span>${{icon}} ${{labelHtml}}</span>
                            </div>
                        </div>`;
                    }}
                }}).join('');

                return `
                <div class="${{cardClass}}" style="display:flex; gap:15px; ${{borderStyle}} align-items:stretch;">
                    <div class="cal-date">
                        <div style="font-weight:800; color:var(--primary); font-size:1.5rem; line-height:1;">${{refEvent.pDate.day}}</div>
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:600;">${{shortMonths[refEvent.pDate.month-1]}}</div>
                    </div>
                    <div style="flex:1; display:flex; flex-direction:column; justify-content:center; position: relative;">
                        ${{badgeHtml}}
                        ${{eventsHtml}}
                    </div>
                </div>`;
            }}).join('');
        }}

        function renderCalendar() {{
            const container = document.getElementById('calendar-list');
            const sorted = [...events].sort((a, b) => {{
                if (a.pDate.month !== b.pDate.month) return a.pDate.month - b.pDate.month;
                return a.pDate.day - b.pDate.day;
            }});

            let lastMonth = -1;
            let html = '';
            
            const grouped = {{}};
            const monthOrder = []; 
            
            sorted.forEach(e => {{
                const key = `${{e.pDate.month}}-${{e.pDate.day}}`;
                if (!grouped[key]) {{
                    grouped[key] = [];
                    monthOrder.push(e); 
                }}
                grouped[key].push(e);
            }});
            
            let currentMonth = -1;
            
            monthOrder.forEach(refEvent => {{
                if (refEvent.pDate.month !== currentMonth) {{
                    html += `<div class="month-header">${{months[refEvent.pDate.month - 1]}}</div>`;
                    currentMonth = refEvent.pDate.month;
                }}
                
                const key = `${{refEvent.pDate.month}}-${{refEvent.pDate.day}}`;
                const dayEvents = grouped[key];
                const processed = processDayEvents(dayEvents);
                
                let rowClass = 'calendar-item';
                if (dayEvents.every(e => e.isPastThisYear)) rowClass += ' is-past';
                if (dayEvents.some(e => e.daysUntil === 0)) rowClass += ' is-today';
                
                const eventsHtml = processed.map(item => {{
                    const icon = item.type === 'Compleanno' ? '🎂' : (item.type === 'Onomastico' ? '🌟' : '💍');
                    const labelHtml = formatLabelHTML(item.label);
                    const colorClass = getColorClass(item.type);
                    
                    if (item.isMerged) {{
                        return `
                        <div class="event-row">
                            <div class="cal-name ${{colorClass}}">${{item.line1}}</div>
                            <div class="cal-name ${{colorClass}}">${{item.line2}}</div>
                            <div class="cal-type"><span>${{icon}} ${{labelHtml}}</span></div>
                        </div>`;
                    }} else {{
                        return `
                        <div class="event-row">
                            <div class="cal-name ${{colorClass}}">${{item.line1}}</div>
                            <div class="cal-type"><span>${{icon}} ${{labelHtml}}</span></div>
                        </div>`;
                    }}
                }}).join('');

                html += `
                <div class="${{rowClass}}">
                    <div class="cal-date">
                        ${{refEvent.pDate.day}}
                        <small>${{shortMonths[refEvent.pDate.month-1]}}</small>
                    </div>
                    <div class="cal-info">
                        ${{eventsHtml}}
                    </div>
                </div>`;
            }});

            container.innerHTML = html;
        }}

        function renderRubrica(filterText = '') {{
            const container = document.getElementById('rubrica-list');
            const countEl = document.getElementById('count-val');
            const clearBtn = document.getElementById('search-clear');
            
            const txt = filterText.toLowerCase();

            if (txt.length > 0) clearBtn.style.display = 'flex';
            else clearBtn.style.display = 'none';

            const people = getGroupedPeople();
            const sortedPeople = Object.values(people).sort((a,b) => a.cognome.localeCompare(b.cognome));
            
            const filtered = sortedPeople.filter(p => 
                p.nome.toLowerCase().includes(txt) || p.cognome.toLowerCase().includes(txt)
            );

            countEl.innerText = filtered.length;

            if (filtered.length === 0) {{
                container.innerHTML = '<p style="text-align:center; padding:2rem; color:var(--text-muted); font-size:1rem;">Nessun risultato</p>';
                return;
            }}

            container.innerHTML = filtered.map(p => {{
                
                const typePriority = {{ 'Compleanno': 1, 'Onomastico': 2, 'Anniversario': 3 }};
                p.items.sort((a, b) => typePriority[a.tipoDisplay] - typePriority[b.tipoDisplay]);

                const itemsHtml = p.items.map(i => {{
                    const icon = i.tipoDisplay === 'Compleanno' ? '🎂' : (i.tipoDisplay === 'Onomastico' ? '🌟' : '💍');
                    
                    let dateStr = '';
                    if (i.tipoDisplay === 'Onomastico') {{
                        dateStr = `${{i.pDate.day}} ${{months[i.pDate.month - 1].toLowerCase()}}`;
                    }} else {{
                        dateStr = `${{i.pDate.day}}/${{i.pDate.month}}`;
                        if (i.pDate.year) {{
                            dateStr += `/${{i.pDate.year}}`;
                        }}
                    }}
                    
                    let rowClass = 'rubrica-row';
                    if (i.isPastThisYear) rowClass += ' is-past-row';
                    
                    let displayLabel = i.tipoDisplay;
                    if (i.currentAge !== null && (i.tipoDisplay === 'Compleanno' || i.tipoDisplay === 'Anniversario')) {{
                         displayLabel += ` (${{i.currentAge}})`;
                    }}
                    
                    displayLabel = formatLabelHTML(displayLabel);

                    return `
                    <div class="${{rowClass}}">
                        <div class="rubrica-type">
                            <span>${{icon}}</span>
                            <span>${{displayLabel}}</span>
                        </div>
                        <div class="rubrica-date">${{dateStr}}</div>
                    </div>`;
                }}).join('');

                return `
                <div class="rubrica-item">
                    <div class="rubrica-name">${{p.cognome}} ${{p.nome}}</div>
                    <div>${{itemsHtml}}</div>
                </div>`;
            }}).join('');
        }}
        
        function getGroupedPeople() {{
            const people = {{}};
            events.forEach(e => {{
                const key = e.Cognome + ' ' + e.Nome;
                if (!people[key]) people[key] = {{ cognome: e.Cognome, nome: e.Nome, items: [] }};
                people[key].items.push(e);
            }});
            return people;
        }}
        
        function clearSearch() {{
            const input = document.getElementById('search-input');
            input.value = '';
            input.focus();
            filterRubrica('');
        }}

        // --- PDF GENERATION ---
        
        function generatePDF() {{
            if (activeTabId === 'rubrica') {{
                generateRubricaPDF();
            }} else {{
                generateCalendarPDF();
            }}
        }}

        function generateRubricaPDF() {{
            const {{ jsPDF }} = window.jspdf;
            
            const doc = new jsPDF({{
                orientation: 'portrait',
                unit: 'mm',
                format: 'a4'
            }});
            
            const pageWidth = doc.internal.pageSize.width;
            const pageHeight = doc.internal.pageSize.height;
            const marginX = 12; 
            const marginY = 15; 
            const colGap = 10;
            const colWidth = (pageWidth - (marginX * 2) - colGap) / 2;
            const nameWidth = 43; 
            
            let cursorY = 15; 
            let currentColumn = 0; 
            let countInColumn = 0; 
            
            doc.setFont("helvetica", "bold");
            doc.setFontSize(16);
            doc.text("Festività parenti e amici", pageWidth / 2, cursorY, {{ align: "center" }});
            
            cursorY += 8; 
            const listStartY = cursorY; 
            
            const people = getGroupedPeople();
            const sortedList = Object.values(people).sort((a, b) => {{
                if (a.cognome !== b.cognome) return a.cognome.localeCompare(b.cognome);
                return a.nome.localeCompare(b.nome);
            }});
            
            doc.setFontSize(9);
            
            const rowHeight = 5; 
            const boxPaddingTop = 4; 
            const boxPaddingBottom = 1; 
            
            let boxStartY = cursorY - boxPaddingTop; 

            sortedList.forEach((p, index) => {{
                let bDayStr = '';
                let nameDayStr = '';
                let annivStr = '';
                
                p.items.forEach(i => {{
                    const d = String(i.pDate.day).padStart(2, '0');
                    const m = String(i.pDate.month).padStart(2, '0');
                    const fullY = i.pDate.year ? i.pDate.year : '';
                    const shortY = fullY ? fullY.slice(-2) : '';
                    
                    if (i.tipoDisplay === 'Compleanno') {{
                        bDayStr = shortY ? `(${{d}}/${{m}}/${{shortY}})` : `(${{d}}/${{m}})`;
                    }} else if (i.tipoDisplay === 'Anniversario') {{
                        annivStr = shortY ? `(${{d}}/${{m}}/${{shortY}})` : `(${{d}}/${{m}})`;
                    }} else if (i.tipoDisplay === 'Onomastico') {{
                        nameDayStr = `[${{d}}-${{m}}]`;
                    }}
                }});
                
                const datesArr = [];
                if (bDayStr) datesArr.push(bDayStr);
                if (nameDayStr) datesArr.push(nameDayStr);
                if (annivStr) datesArr.push(annivStr);
                const datesText = datesArr.join('   '); 

                if (cursorY > pageHeight - marginY) {{
                    if (countInColumn % 10 !== 0) {{
                        const xBaseOld = marginX + (currentColumn * (colWidth + colGap));
                        let boxBottom = cursorY - rowHeight + boxPaddingBottom;
                        
                        doc.setDrawColor(180, 180, 180);
                        doc.setLineWidth(0.1);
                        doc.rect(xBaseOld - 1, boxStartY, colWidth + 2, boxBottom - boxStartY);
                        doc.setDrawColor(0);
                    }}

                    if (currentColumn === 0) {{
                        currentColumn = 1;
                        cursorY = listStartY; 
                    }} else {{
                        doc.addPage();
                        currentColumn = 0;
                        cursorY = 15; 
                    }}
                    
                    boxStartY = cursorY - boxPaddingTop;
                }}
                
                const xBase = marginX + (currentColumn * (colWidth + colGap));
                const xDate = xBase + nameWidth; 
                
                doc.setFont("helvetica", "normal");
                const nameStr = `${{p.cognome}} ${{p.nome}}`;
                doc.text(nameStr, xBase, cursorY);
                
                const textWidth = doc.getTextWidth(nameStr);
                const lineStart = xBase + textWidth + 1; 
                const lineEnd = xDate - 1; 
                
                if (lineEnd > lineStart) {{
                    doc.setDrawColor(180, 180, 180);
                    doc.setLineWidth(0.1); 
                    doc.setLineDash([0.5, 0.5], 0); 
                    doc.line(lineStart, cursorY, lineEnd, cursorY);
                    doc.setDrawColor(0);
                    doc.setLineDash([]);
                }}
                
                doc.text(datesText, xDate, cursorY);
                
                cursorY += rowHeight;
                countInColumn++;
                
                if (countInColumn > 0 && (countInColumn % 10 === 0 || index === sortedList.length - 1)) {{
                    let boxBottom = cursorY - rowHeight + boxPaddingBottom;
                    let h = boxBottom - boxStartY;
                    
                    doc.setDrawColor(180, 180, 180); 
                    doc.setLineWidth(0.1);
                    doc.rect(xBase - 1, boxStartY, colWidth + 2, h); 
                    doc.setDrawColor(0);
                    
                    cursorY += 3;
                    boxStartY = cursorY - boxPaddingTop;
                }}
            }});
            
            window.open(doc.output('bloburl'), '_blank');
        }}

        function generateCalendarPDF() {{
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF({{ orientation: 'portrait', unit: 'mm', format: 'a4' }});
            
            const year = new Date().getFullYear();
            const pageWidth = doc.internal.pageSize.width;
            const pageHeight = doc.internal.pageSize.height;
            const margin = 20; 
            const colGap = 10;
            const colWidth = (pageWidth - (margin * 2) - colGap) / 2;
            
            for (let m = 0; m < 12; m++) {{
                if (m > 0) doc.addPage();
                
                doc.setFont("helvetica", "bold");
                doc.setFontSize(20);
                doc.setTextColor(0,0,0);
                doc.text(`${{months[m]}} ${{year}}`, pageWidth/2, 15, {{align: "center"}});
                
                const monthlyEvents = events.filter(e => e.pDate.month === (m + 1));
                
                const eventsByDay = {{}};
                monthlyEvents.forEach(e => {{
                    if (!eventsByDay[e.pDate.day]) eventsByDay[e.pDate.day] = [];
                    eventsByDay[e.pDate.day].push(e);
                }});
                
                const sortedDays = Object.keys(eventsByDay).map(Number).sort((a,b) => a-b);
                
                let cursorY = 25;
                let col = 0; 
                let startY = cursorY;
                
                sortedDays.forEach(day => {{
                    const dayEvents = eventsByDay[day];
                    const mergedList = processDayEvents(dayEvents); 
                    
                    let totalBoxHeight = 0;
                    const itemSpacing = 2; 
                    
                    mergedList.forEach((item, idx) => {{
                        const h = item.isMerged ? 16 : 11;
                        totalBoxHeight += h;
                        if (idx < mergedList.length - 1) totalBoxHeight += itemSpacing;
                    }});
                    
                    totalBoxHeight += 6; 
                    
                    if (cursorY + totalBoxHeight > pageHeight - margin) {{
                        if (col === 0) {{
                            col = 1;
                            cursorY = startY; 
                        }} else {{
                            doc.addPage();
                            doc.text(`${{months[m]}} ${{year}} (cont.)`, pageWidth/2, 15, {{align: "center"}});
                            col = 0;
                            cursorY = 25;
                            startY = 25;
                        }}
                    }}
                    
                    const xBase = margin + (col * (colWidth + colGap));
                    
                    doc.setFillColor(230, 230, 230);
                    doc.rect(xBase + 1, cursorY + 1, colWidth, totalBoxHeight, 'F'); 
                    doc.setFillColor(255, 255, 255);
                    doc.setDrawColor(200, 200, 200);
                    doc.rect(xBase, cursorY, colWidth, totalBoxHeight, 'FD'); 
                    doc.setDrawColor(0);
                    
                    const dateBoxWidth = 14;
                    const dayCenterY = cursorY + (totalBoxHeight / 2);
                    
                    const eventDateObj = new Date(year, m, day);
                    const dayName = eventDateObj.toLocaleDateString('it-IT', {{ weekday: 'short' }}).toUpperCase().substring(0,3);
                    
                    doc.setFontSize(8);
                    doc.setFont("helvetica", "normal");
                    doc.setTextColor(100, 100, 100);
                    doc.text(dayName, xBase + (dateBoxWidth/2), dayCenterY - 3, {{align: "center"}});
                    
                    doc.setFontSize(14);
                    doc.setFont("helvetica", "bold");
                    doc.setTextColor(0, 0, 0); 
                    doc.text(String(day), xBase + (dateBoxWidth/2), dayCenterY + 3, {{align: "center"}});
                    
                    doc.setDrawColor(220, 220, 220);
                    doc.line(xBase + dateBoxWidth, cursorY + 2, xBase + dateBoxWidth, cursorY + totalBoxHeight - 2);
                    
                    let currentTextY = cursorY + 3; 
                    const textX = xBase + dateBoxWidth + 3;
                    
                    mergedList.forEach(item => {{
                        
                        // SET COLOR BASED ON TYPE
                        if (item.type === 'Compleanno') doc.setTextColor(0, 51, 102); // Dark Blue
                        else if (item.type === 'Onomastico') doc.setTextColor(0, 100, 0); // Dark Green
                        else if (item.type === 'Anniversario') doc.setTextColor(153, 0, 51); // Porpora/Crimson
                        else doc.setTextColor(0,0,0);

                        doc.setFontSize(10);
                        doc.setFont("helvetica", "bold");
                        
                        if (item.isMerged) {{
                            doc.text(item.line1, textX, currentTextY + 4);
                            doc.text(item.line2, textX, currentTextY + 8.5); 
                            
                            // Reset to gray for label
                            doc.setTextColor(80, 80, 80);
                            drawLabelWithBoldNumber(doc, item.label, textX, currentTextY + 13);
                            
                            currentTextY += 16 + itemSpacing;
                        }} else {{
                            doc.text(item.line1, textX, currentTextY + 4);
                            
                            // Reset to gray for label
                            doc.setTextColor(80, 80, 80);
                            drawLabelWithBoldNumber(doc, item.label, textX, currentTextY + 8.5);
                            
                            currentTextY += 11 + itemSpacing;
                        }}
                    }});
                    
                    cursorY += totalBoxHeight + 3; 
                }});
            }}
            
            window.open(doc.output('bloburl'), '_blank');
        }}
        
        function drawLabelWithBoldNumber(doc, text, x, y) {{
            const regex = /(.*)(\\(\\d+\\))(.*)/; 
            const match = text.match(regex);
            
            doc.setFontSize(9);
            // Color is already set to grey before calling this
            
            if (match) {{
                const prefix = match[1];
                const numberPart = match[2]; 
                
                doc.setFont("helvetica", "normal");
                doc.text(prefix, x, y);
                const w1 = doc.getTextWidth(prefix);
                
                doc.setFont("helvetica", "bold");
                doc.setTextColor(0,0,0); // Number in black
                doc.text(numberPart, x + w1, y);
            }} else {{
                doc.setFont("helvetica", "normal");
                doc.text(text, x, y);
            }}
        }}

        function renderStats() {{
            const mCount = new Array(12).fill(0);
            events.forEach(e => mCount[e.pDate.month-1]++);
            const maxM = Math.max(...mCount);
            document.getElementById('stats-months').innerHTML = months.map((m, i) => {{
                if (mCount[i] === 0) return '';
                const w = (mCount[i]/maxM)*100;
                return `<div style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;">
                            <div style="width:100px;">${{m}}</div>
                            <div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;">
                                <div style="height:100%;width:${{w}}%;background:var(--primary);border-radius:6px;"></div>
                            </div>
                            <div style="font-weight:bold;">${{mCount[i]}}</div>
                        </div>`;
            }}).join('');

            const tCount = {{ 'Compleanno': 0, 'Onomastico': 0, 'Anniversario': 0 }};
            events.forEach(e => {{
                if (tCount[e.tipoDisplay] !== undefined) tCount[e.tipoDisplay]++;
                else tCount['Anniversario']++;
            }});
            const maxT = Math.max(...Object.values(tCount));
            document.getElementById('stats-types').innerHTML = Object.entries(tCount).map(([k, v]) => {{
                if (v === 0) return '';
                const w = (v/maxT)*100;
                return `<div style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;">
                            <div style="width:100px;">${{k}}</div>
                            <div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;">
                                <div style="height:100%;width:${{w}}%;background:#ec4899;border-radius:6px;"></div>
                            </div>
                            <div style="font-weight:bold;">${{v}}</div>
                        </div>`;
            }}).join('');

            const peopleGender = {{ 'M': 0, 'F': 0 }};
            const uniqueKeys = new Set();
            events.forEach(e => {{
                const k = e.Cognome + '|' + e.Nome;
                if (!uniqueKeys.has(k)) {{
                    uniqueKeys.add(k);
                    let g = e.Genere ? e.Genere.toUpperCase().trim() : 'M';
                    if (peopleGender[g] !== undefined) peopleGender[g]++;
                }}
            }});
        
            const maxG = Math.max(peopleGender['M'], peopleGender['F']) || 1;
            const genderHtml = [
                {{ label: 'Maschile', count: peopleGender['M'], color: 'var(--primary)' }},
                {{ label: 'Femminile', count: peopleGender['F'], color: '#ec4899' }}
            ].map(item => {{
                const w = (item.count / maxG) * 100;
                return `<div style="display:flex;align-items:center;margin-bottom:10px;font-size:0.9rem;">
                            <div style="width:100px;">${{item.label}}</div>
                            <div style="flex:1;height:10px;background:#f1f5f9;border-radius:6px;margin:0 10px;">
                                <div style="height:100%;width:${{w}}%;background:${{item.color}};border-radius:6px;"></div>
                            </div>
                            <div style="font-weight:bold;">${{item.count}}</div>
                        </div>`;
            }}).join('');
            
            document.getElementById('stats-gender').innerHTML = genderHtml;
        }}

        let calendarScrollId = null;

        function switchTab(tabId) {{
            activeTabId = tabId; // Aggiorna stato
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            
            document.getElementById('tab-' + tabId).classList.add('active');
            document.querySelector(`button[onclick="switchTab('${{tabId}}')"]`).classList.add('active');

            const appContainer = document.getElementById('app-container');
            if (tabId === 'home' || tabId === 'stats') {{
                appContainer.classList.add('bg-yellow-mode');
            }} else {{
                appContainer.classList.remove('bg-yellow-mode');
            }}

            if (tabId === 'calendario' && calendarScrollId) {{
                setTimeout(() => {{
                    const el = document.getElementById(calendarScrollId);
                    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}, 100);
            }} else {{
                window.scrollTo(0,0);
            }}
        }}

        function filterRubrica() {{
            renderRubrica(document.getElementById('search-input').value);
        }}

        let touchStartY = 0;
        let touchEndY = 0;
        const indicator = document.getElementById('refresh-indicator');

        document.addEventListener('touchstart', e => {{
            touchStartY = e.touches[0].clientY;
        }}, {{passive: true}});

        document.addEventListener('touchmove', e => {{
            touchEndY = e.touches[0].clientY;
            if (window.scrollY === 0 && touchEndY > touchStartY + 50) {{
                indicator.classList.add('show');
            }}
        }}, {{passive: true}});

        document.addEventListener('touchend', e => {{
            indicator.classList.remove('show');
            if (window.scrollY === 0 && touchEndY > touchStartY + 150) {{
                window.location.reload();
            }}
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            renderHome();
            renderRubrica();
            calendarScrollId = renderCalendar(); 
            renderStats();
            document.getElementById('app-container').classList.add('bg-yellow-mode');
        }});

    </script>
</body>
</html>"""
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"🎉 Successo! File generato: {OUTPUT_FILE}")
    
    try:
        file_path = os.path.abspath(OUTPUT_FILE)
        webbrowser.open(f'file://{file_path}')
        print(f"🚀 Apertura file nel browser...")
    except Exception as e:
        print(f"⚠️ Impossibile aprire il browser automaticamente: {e}")

if __name__ == "__main__":
    target_date = None
    # Verifica se c'è un argomento nel formato data GG-MM-AAAA
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        try:
            target_date = datetime.strptime(arg, "%d-%m-%Y")
            print(f"🕒 MODALITÀ VIAGGIO NEL TEMPO ATTIVA: {target_date.strftime('%d/%m/%Y')}")
        except ValueError:
            print("⚠️ Formato data non valido (Usa GG-MM-AAAA). Uso data odierna.")
    
    dati_csv = leggi_e_processa_dati(INPUT_FILE)
    if dati_csv:
        genera_html(dati_csv, target_date)
        genera_txt_siri_discorsivo(dati_csv, target_date)