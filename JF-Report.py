# Nome script: jf-report.py
# Data modifica: 29/12/2025 - FIX SORT & COPY NEWLINE
# Descrizione: Genera l'ecosistema report JOYFIT.
#
# AGGIORNAMENTI:
# 1. SCHEDA CLIENTE: Corretto ordinamento colonne (Data/Attività/Importo).
# 2. COPIA: Aggiunto ritorno a capo finale dopo i trattini.

import pdfplumber
import os
import re
import webbrowser
import json
import calendar
import requests
import io
import csv
import difflib
from datetime import datetime

# --- CONFIGURAZIONE ---
INPUT_PDF_URL = r"C:\Dropbox\Prog\Monitor\JF-Calendari.pdf"
INPUT_DATE_FILE = r"C:\Dropbox\Prog\Monitor\JF-DB.txt"
INPUT_CSV_FILE  = r"C:\Dropbox\Prog\Monitor\JF-DB.csv"
INPUT_DUPLICATI_FILE = r"C:\Dropbox\Prog\Monitor\JF-Duplicati.txt" 

# LIMITI ANNO SPORTIVO
START_DATE = datetime(2025, 9, 1)
END_DATE   = datetime(2026, 8, 31)

# URL Risorse
ICON_URL = "https://raw.githubusercontent.com/Sebastiano-Mazzarisi/Test/main/JoyFit.jpg"

# Percorsi Output
OUTPUT_DIR = r"C:\Dropbox\Prog\Monitor"
OUTPUT_REPORT = os.path.join(OUTPUT_DIR, "JF-Report.html")
OUTPUT_ADMIN  = os.path.join(OUTPUT_DIR, "JF-Report-ADMIN.html")
OUTPUT_CONTA  = os.path.join(OUTPUT_DIR, "JF-Conta.html")

# Backup path
OUTPUT_DIR_JF = r"C:\Dropbox\Prog\JF"
OUTPUT_REPORT_JF = os.path.join(OUTPUT_DIR_JF, "JF-Report.html")

MESI_ORDINE = ["SET", "OTT", "NOV", "DIC", "GEN", "FEB", "MAR", "APR", "MAG", "GIU", "LUG", "AGO"]
MESI_NUM = {
    "SET": 9, "OTT": 10, "NOV": 11, "DIC": 12,
    "GEN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAG": 5, "GIU": 6, "LUG": 7, "AGO": 8
}
GIORNI_SETT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
GIORNI_FULL = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]

# --- FUNZIONI DI UTILITÀ ---
def pulisci_importo(valore_str):
    if not valore_str: return 0.0
    v = str(valore_str).replace("€", "").replace(" ", "").strip()
    v = v.replace(".", "") 
    v = v.replace(",", ".") 
    try: return float(v)
    except ValueError: return 0.0

def formatta_num(n):
    return f"{n:,.0f}".replace(",", ".")

def leggi_data_da_file_txt(path_txt):
    if not os.path.exists(path_txt): return None
    try:
        with open(path_txt, "r", encoding="utf-8") as f:
            content = f.read(500)
            matches = re.findall(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", content)
            return matches[-1] if matches else None
    except: return None

def apri_pdf_da_sorgente(path_or_url):
    try:
        if path_or_url.startswith("http"):
            print(f"Scaricamento PDF da: {path_or_url}...")
            response = requests.get(path_or_url, timeout=10)
            response.raise_for_status()
            return pdfplumber.open(io.BytesIO(response.content))
        else:
            if os.path.exists(path_or_url):
                print(f"Apertura PDF locale: {path_or_url}...")
                return pdfplumber.open(path_or_url)
            else:
                print(f"File PDF non trovato: {path_or_url}")
            return None
    except Exception as e:
        print(f"Errore apertura PDF: {e}")
        return None

def carica_esclusioni_duplicati(path_txt):
    esclusioni = set()
    if not os.path.exists(path_txt):
        return esclusioni
    try:
        with open(path_txt, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "," not in line: continue
                parts = line.split(",")
                if len(parts) >= 2:
                    n1 = parts[0].strip().lower()
                    n2 = parts[1].strip().lower()
                    if n1 and n2:
                        esclusioni.add(tuple(sorted((n1, n2))))
    except: pass
    return esclusioni

# --- PARSING CSV ---
def carica_dati_csv(path_csv):
    dati_trans = {m: {} for m in MESI_ORDINE}
    all_transactions = [] 
    totals_map = {} 
    
    if not os.path.exists(path_csv):
        return dati_trans, all_transactions, {}

    csv_encoding = 'utf-8-sig'
    try:
        with open(path_csv, "r", encoding=csv_encoding) as f: f.read(1024)
    except UnicodeDecodeError:
        csv_encoding = 'latin1'

    try:
        with open(path_csv, "r", encoding=csv_encoding, errors="replace") as f:
            sample = f.read(1024)
            f.seek(0)
            delimiter = ';' if ';' in sample else ','
            reader = csv.reader(f, delimiter=delimiter)
            
            header_skipped = False
            for row in reader:
                if not row: continue
                if not header_skipped:
                    row_str = "".join(row).lower()
                    if "data" in row_str and "nominativo" in row_str:
                        header_skipped = True
                        continue
                if len(row) <= 6: continue
                
                raw_date = row[1].strip()
                raw_nominativo = row[2].strip()
                
                if raw_nominativo:
                    if not raw_nominativo[0].isalpha(): 
                        nominativo = "[Altro]"
                    else:
                        nominativo = raw_nominativo.title() 
                else: 
                    nominativo = "[Altro]"

                raw_att = row[3].strip() if len(row) > 3 else ""
                raw_contanti = row[5].strip()
                raw_pos = row[6].strip()
                
                dt_obj = None
                for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                    try: dt_obj = datetime.strptime(raw_date, fmt); break
                    except: pass
                
                if dt_obj:
                    if not (START_DATE <= dt_obj <= END_DATE): continue

                    val = pulisci_importo(raw_contanti) + pulisci_importo(raw_pos)
                    if val <= 0: continue

                    if nominativo not in totals_map: totals_map[nominativo] = 0.0
                    totals_map[nominativo] += val

                    all_transactions.append({
                        "date_str": dt_obj.strftime("%d/%m/%Y"),
                        "ts": dt_obj.timestamp(),
                        "nome": nominativo,
                        "att": raw_att,
                        "imp": val
                    })

                    mese_idx = dt_obj.month
                    mese_str = None
                    for k, v in MESI_NUM.items():
                        if v == mese_idx: mese_str = k; break
                    
                    if mese_str and mese_str in dati_trans:
                        giorno = dt_obj.day
                        if giorno not in dati_trans[mese_str]: dati_trans[mese_str][giorno] = []
                        dati_trans[mese_str][giorno].append({"nome": nominativo, "imp": val})
                        
    except Exception as e: print(f"Errore critico lettura CSV: {e}")

    # --- CALCOLO DUPLICATI ---
    duplicates_map = {}
    exclusion_rules = carica_esclusioni_duplicati(INPUT_DUPLICATI_FILE)

    valid_names = [name for name, tot in totals_map.items() if tot > 0 and name != "[Altro]"]
    sorted_names = sorted(valid_names)
    
    names_by_initial = {}
    for name in sorted_names:
        initial = name[0].upper()
        if initial not in names_by_initial: names_by_initial[initial] = []
        names_by_initial[initial].append(name)
        
    for initial, group in names_by_initial.items():
        if len(group) < 2: continue
        for name in group:
            matches = difflib.get_close_matches(name, group, n=5, cutoff=0.85)
            matches = [m for m in matches if m != name]
            
            filtered_matches = []
            if matches:
                name_lower = name.lower()
                for candidate in matches:
                    candidate_lower = candidate.lower()
                    is_excluded = False
                    for rule_n1, rule_n2 in exclusion_rules:
                        cond1 = (rule_n1 in name_lower and rule_n2 in candidate_lower)
                        cond2 = (rule_n2 in name_lower and rule_n1 in candidate_lower)
                        if cond1 or cond2:
                            is_excluded = True
                            break
                    if not is_excluded:
                        filtered_matches.append(candidate)
            
            if filtered_matches:
                duplicates_map[name] = filtered_matches

    return dati_trans, all_transactions, duplicates_map

# --- PARSING PDF ---
def estrai_dati_completi(pdf_source):
    dati_mensili = {"2024-25": {m: 0.0 for m in MESI_ORDINE}, "2025-26": {m: 0.0 for m in MESI_ORDINE}}
    dati_giornalieri = {m: [] for m in MESI_ORDINE}
    
    pdf = apri_pdf_da_sorgente(pdf_source)
    if not pdf: return dati_mensili, dati_giornalieri

    try:
        for page in pdf.pages:
            text = page.extract_text()
            tables = page.extract_table()
            anno_corr = None
            if text and "2025-26" in text: anno_corr = "2025-26"
            elif text and "2024-25" in text: anno_corr = "2024-25"
            
            if anno_corr and tables:
                header_idx = -1
                for i, row in enumerate(tables):
                    row_cl = [str(x).strip().upper()[:3] for x in row if x]
                    if sum(1 for x in row_cl if x in MESI_ORDINE) > 5: header_idx = i; break
                if header_idx != -1:
                    headers = tables[header_idx]
                    for row in tables[header_idx+1:]:
                        for col_idx, cell_val in enumerate(row):
                            if col_idx < len(headers) and cell_val:
                                mese = str(headers[col_idx]).strip().upper()[:3].replace('"','')
                                if mese in MESI_ORDINE:
                                    cell_str = str(cell_val)
                                    nums = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", cell_str)
                                    vals = [pulisci_importo(n) for n in nums]
                                    match_day = re.search(r"\b(\d{1,2})\s+(Lu|Ma|Me|Gi|Ve|Sa|Do)\b", cell_str, re.IGNORECASE)
                                    
                                    if anno_corr == "2025-26":
                                        if match_day:
                                            val_giorno = 0.0
                                            if len(vals) > 0:
                                                possibili = [v for v in vals if v < 10000]
                                                if vals: val_giorno = possibili[-1]
                                                if vals: dati_mensili[anno_corr][mese] = max(dati_mensili[anno_corr][mese], max(vals))
                                            
                                            if val_giorno > 0:
                                                g_num = int(match_day.group(1))
                                                esistente = False
                                                for d in dati_giornalieri[mese]:
                                                    if d["num"] == g_num: d["valore"] = max(d["valore"], val_giorno); esistente = True; break
                                                if not esistente: dati_giornalieri[mese].append({"num": g_num, "valore": val_giorno})
                                        else:
                                            if vals: dati_mensili[anno_corr][mese] = max(dati_mensili[anno_corr][mese], max(vals))
                                    else:
                                        if vals: dati_mensili[anno_corr][mese] = max(dati_mensili[anno_corr][mese], max(vals))
    except Exception as e: print(f"Errore analisi PDF: {e}")
    finally: pdf.close()

    for m in MESI_ORDINE: dati_giornalieri[m].sort(key=lambda x: x["num"])
    return dati_mensili, dati_giornalieri

# --- GENERAZIONE HTML REPORT ---

def genera_html_report(dati_mensili, dati_giornalieri, dati_transazioni, all_transactions, dupe_map, data_rif_str, is_admin_version=False):
    try: data_rif_dt = datetime.strptime(data_rif_str, "%d/%m/%Y")
    except: data_rif_dt = datetime.now()

    json_data = {}
    tot_annuo_24_25 = sum(dati_mensili["2024-25"].values())
    tot_annuo_consuntivo = 0.0
    tot_annuo_proiettato = 0.0
    
    global_aggregator = {}
    global_day_index = []

    for mese in MESI_ORDINE:
        mese_num = MESI_NUM[mese]
        anno_ref = 2025 if mese_num >= 9 else 2026
        val_24_25 = dati_mensili["2024-25"][mese]
        val_25_26_tot = dati_mensili["2025-26"][mese]
        map_giorni = {item["num"]: item["valore"] for item in dati_giornalieri[mese]}
        num_giorni_mese = calendar.monthrange(anno_ref, mese_num)[1]
        
        lista_giorni = []
        tot_cons_mese = 0.0
        tot_prev_mese = 0.0
        daily_details = {} 
        
        # Calcolo Data Pareggio Mensile
        breakeven_day_str = None
        running_cons_sum = 0.0

        for d in range(1, num_giorni_mese + 1):
            dt_curr = datetime(anno_ref, mese_num, d)
            giorno_sett_idx = dt_curr.weekday()
            giorno_str = f"{d:02d} {GIORNI_SETT[giorno_sett_idx]}"
            
            nome_giorno_full = GIORNI_FULL[giorno_sett_idx]
            data_full_str = f"{d}/{mese_num}/{anno_ref}"

            val = map_giorni.get(d, 0.0)
            
            raw_trans_list = dati_transazioni[mese].get(d, [])
            
            if dt_curr <= data_rif_dt:
                c, p = val, 0.0
                tot_cons_mese += val
                
                # Check Breakeven
                running_cons_sum += val
                if not breakeven_day_str and val_24_25 > 0 and running_cons_sum >= val_24_25:
                    breakeven_day_str = f"{d}/{mese_num}"
                
                if raw_trans_list:
                    agg_map = {}
                    for t in raw_trans_list:
                        nm = t["nome"]; im = t["imp"]
                        if nm in agg_map: agg_map[nm] += im
                        else: agg_map[nm] = im
                        
                        if nm not in global_aggregator:
                            global_aggregator[nm] = {"total": 0.0, "last_date_dt": dt_curr}
                        global_aggregator[nm]["total"] += im
                        if dt_curr > global_aggregator[nm]["last_date_dt"]:
                            global_aggregator[nm]["last_date_dt"] = dt_curr

                    final_list = []
                    for nm, im in agg_map.items(): final_list.append({"nome": nm, "imp": im})
                    final_list.sort(key=lambda x: x["nome"].lower())
                    
                    anno_short = str(anno_ref)[-2:]
                    daily_details[str(d)] = {
                        "date_full": f"{d}/{mese_num}/{anno_short}",
                        "title_day_name": nome_giorno_full,
                        "title_date": data_full_str,
                        "trans": final_list,
                        "tot_day": sum(t["imp"] for t in final_list)
                    }
                    global_day_index.append({ "m": mese, "d": d, "ts": dt_curr.timestamp() })
            else:
                c, p = 0.0, val
                tot_prev_mese += val
                
            lista_giorni.append({"giorno": giorno_str, "cons": c, "prev": p, "day_num": d})

        somma_giorni = tot_cons_mese + tot_prev_mese
        if somma_giorni == 0 and val_25_26_tot > 0:
            dt_inizio = datetime(anno_ref, mese_num, 1)
            if dt_inizio > data_rif_dt: tot_prev_mese = val_25_26_tot
            elif dt_inizio.month == data_rif_dt.month and dt_inizio.year == data_rif_dt.year: tot_prev_mese = val_25_26_tot
            else: tot_cons_mese = val_25_26_tot
        elif val_25_26_tot > somma_giorni:
             diff = val_25_26_tot - somma_giorni
             if datetime(anno_ref, mese_num, 1) > data_rif_dt: tot_prev_mese += diff
             else: tot_cons_mese += diff

        tot_mese_calc = tot_cons_mese + tot_prev_mese
        tot_annuo_consuntivo += tot_cons_mese
        tot_annuo_proiettato += tot_mese_calc
        
        prev_home_txt = ""
        prev_home_style = ""
        if tot_prev_mese > 0:
             prev_home_txt = formatta_num(tot_prev_mese)
             prev_home_style = "bg-yellow"
        elif tot_cons_mese > 0 and val_24_25 > 0:
             diff = ((tot_cons_mese - val_24_25) / val_24_25) * 100
             prev_home_txt = f"{diff:+.1f}%".replace('.', ',')
             prev_home_style = "text-pct-small"
        
        mese_full = ""
        if mese == "SET": mese_full = "SETTEMBRE"
        elif mese == "OTT": mese_full = "OTTOBRE"
        elif mese == "NOV": mese_full = "NOVEMBRE"
        elif mese == "DIC": mese_full = "DICEMBRE"
        elif mese == "GEN": mese_full = "GENNAIO"
        elif mese == "FEB": mese_full = "FEBBRAIO"
        elif mese == "MAR": mese_full = "MARZO"
        elif mese == "APR": mese_full = "APRILE"
        elif mese == "MAG": mese_full = "MAGGIO"
        elif mese == "GIU": mese_full = "GIUGNO"
        elif mese == "LUG": mese_full = "LUGLIO"
        elif mese == "AGO": mese_full = "AGOSTO"

        json_data[mese] = {
            "nome_esteso": f"{mese} {anno_ref}",
            "title_mese": mese_full,
            "title_anno": str(anno_ref),
            "tot_24_25": val_24_25,
            "tot_cons": tot_cons_mese,
            "tot_prev": tot_prev_mese,
            "tot_full": tot_mese_calc,
            "lista_giorni": lista_giorni,
            "dettagli": daily_details,
            "breakeven": breakeven_day_str,
            "home_data": {
                "old": formatta_num(val_24_25) if val_24_25 > 0 else "",
                "cons": formatta_num(tot_cons_mese) if tot_cons_mese > 0 else "",
                "prev_txt": prev_home_txt,
                "prev_style": prev_home_style
            }
        }

    global_day_index.sort(key=lambda x: x["ts"])
    json_data["GLOBAL_DAY_INDEX"] = global_day_index

    # GLOBAL LIST
    global_list = []
    for nm, data in global_aggregator.items():
        d_str = data["last_date_dt"].strftime("%d/%m/%Y")
        d_ts = data["last_date_dt"].timestamp()
        global_list.append({ "nome": nm, "imp": data["total"], "last_date": d_str, "ts": d_ts })
    global_list.sort(key=lambda x: x["nome"].lower())
    json_data["GLOBAL_LIST"] = global_list
    
    # ALL TRANSACTIONS
    json_data["ALL_TRANSACTIONS"] = sorted(all_transactions, key=lambda x: x['ts'])
    
    # DUPLICATES
    json_data["DUPLICATES_MAP"] = dupe_map

    max_val_home = max(tot_annuo_24_25, tot_annuo_proiettato) if tot_annuo_proiettato > 0 else 1
    pct_24_25 = (tot_annuo_24_25 / max_val_home) * 100
    pct_consuntivo = (tot_annuo_consuntivo / max_val_home) * 100
    pct_totale = (tot_annuo_proiettato / max_val_home) * 100

    # CREATE FORECAST TIMELINE
    forecast_timeline = []
    for m_code in MESI_ORDINE:
        m_num = MESI_NUM[m_code]
        y_ref = 2025 if m_num >= 9 else 2026
        day_map = {x["num"]: x["valore"] for x in dati_giornalieri[m_code]}
        days_in_month = calendar.monthrange(y_ref, m_num)[1]
        for d in range(1, days_in_month + 1):
            dt = datetime(y_ref, m_num, d)
            val = day_map.get(d, 0.0)
            forecast_timeline.append({
                "ts": dt.timestamp(),
                "date": dt.strftime("%d/%m/%Y"),
                "val": val
            })
    json_data["FORECAST_TIMELINE"] = forecast_timeline

    json_data["GLOBAL_STATS"] = { 
        "tot_annuo": tot_annuo_consuntivo,
        "tot_ref": tot_annuo_24_25,
        "tot_cons": tot_annuo_consuntivo,
        "tot_prev": tot_annuo_proiettato,
        "data_rif": data_rif_str
    }
    js_admin_flag = "true" if is_admin_version else "false"

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Report</title>
    <meta name="apple-mobile-web-app-title" content="Report">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <link rel="icon" type="image/jpeg" href="{ICON_URL}">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <style>
        body {{ 
            background-color: #cfd8dc; 
            font-family: -apple-system, sans-serif; 
            font-size: 26px; 
            padding: 10px 0; 
            color: #111827; 
            overscroll-behavior-y: none;
        }}
        
        #loading-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); z-index: 9999;
            display: none; flex-direction: column; justify-content: center; align-items: center;
            color: white; font-size: 2rem; font-weight: bold; text-align: center;
        }}

        #copy-toast {{
            position: fixed;
            top: 50%; left: 50%; transform: translate(-50%, -50%);
            background-color: #e5e7eb; color: black;
            padding: 15px 25px; border-radius: 8px;
            font-weight: bold; font-size: 1.2rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            z-index: 20000; display: none;
        }}
        
        .popup-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.6); z-index: 10000;
            display: none; justify-content: center; align-items: center;
        }}
        .popup-content {{
            background: white; border-radius: 12px; padding: 25px; width: 90%; max-width: 400px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3); position: relative;
            font-size: 1.2rem; line-height: 1.5; color: #333;
        }}
        .popup-header {{
            background-color: #1a3b5c; color: white; padding: 15px; 
            text-align: center; font-weight: 800; font-size: 1.4rem;
            text-transform: uppercase;
            border-radius: 12px 12px 0 0;
            margin: -25px -25px 20px -25px;
        }}
        .popup-close-btn {{
            position: absolute; top: 12px; right: 15px; font-size: 1.8rem;
            cursor: pointer; color: white; font-weight: bold; line-height: 1;
            z-index: 10001;
        }}
        .popup-row {{ margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .popup-row:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        .popup-label {{ font-size: 1rem; color: #666; text-transform: uppercase; font-weight: bold; }}
        .popup-val {{ font-size: 1.6rem; font-weight: 800; color: #111; display: flex; align-items: baseline; justify-content: space-between; }}
        .popup-diff {{ font-size: 1rem; font-weight: normal; margin-left: 10px; }}
        .popup-missing {{ font-size: 1.1rem; color: #dc2626; margin-top: 5px; font-weight: 600; text-align:right; }}
        .popup-breakeven {{ font-size: 1.1rem; color: #1a3b5c; margin-top: 5px; font-weight: bold; font-style: normal; text-transform:uppercase; }}
        
        .main-wrapper {{ 
            width: 94%; 
            max-width: 600px; 
            margin: 0 auto;
            border: none; 
            padding: 0;
            background-color: transparent; 
            box-shadow: none;
        }}
        
        .card-box {{ background: white; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); overflow: hidden; margin-bottom: 20px; border: 1px solid black; transform: translateZ(0); padding-bottom: 1px; }}
        .header-blue {{ background-color: #1a3b5c; color: white; padding: 10px 10px; display: flex; justify-content: space-between; align-items: center; height: 90px; }}
        
        .header-title {{ 
            font-size: 1.6rem; 
            font-weight: 800; 
            margin: 0; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            cursor: pointer; 
            line-height: 1.1; 
            white-space: normal;
            text-align: center;
        }}
        
        .btn-styled {{ 
            background-color: #f1f5f9; color: #1a3b5c !important; border-radius: 8px; 
            padding: 5px 12px; font-size: 1.8rem; cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2); display: inline-block; transition: background 0.2s;
        }}
        .btn-styled:active {{ background-color: #e2e8f0; }}
        
        .btn-home {{ text-decoration: none; }}
        .btn-audio {{ text-decoration: none; margin-right: 10px; }}
        .btn-user {{ text-decoration: none; font-size: 2rem; }} 
        
        .nav-arrow {{ color: {'#ffff00' if is_admin_version else 'white'}; font-size: 2.5rem; cursor: pointer; font-weight: bold; padding: 0 15px; user-select: none; {'text-shadow: 0 0 5px #000;' if is_admin_version else ''} }}
        .nav-arrow-up {{ font-size: 2rem; cursor: pointer; color: {'#ffff00' if is_admin_version else 'white'}; padding: 0 10px; }}
        
        .total-box {{ background: #fff; padding: 30px 20px; text-align: center; border-bottom: 1px solid #eee; }}
        .total-amount {{ font-size: 4.8rem; font-weight: 900; color: #d97706; line-height: 1; margin: 0; transition: opacity 1s ease-in-out; opacity: 1; }}
        
        .chart-section {{ padding: 25px 20px; }}
        .bar-row {{ display: flex; align-items: center; margin-bottom: 5px; font-size: 1.2rem; cursor: pointer; }}
        .bar-label-container {{ width: 145px; flex-shrink: 0; text-align: center; margin-right: 5px; }}
        .bar-label-text {{ font-weight: 700; color: #000 !important; font-size: 1.3rem; border: 4px solid transparent; border-radius: 4px; padding: 2px 5px; display: inline-block; white-space: nowrap; }}
        .bar-value {{ width: 140px; text-align: right; font-weight: 800; color: #000 !important; font-size: 1.3rem; flex-shrink: 0; }}
        .progress {{ flex-grow: 1; height: 26px; margin: 0 15px; border-radius: 8px; width: 40%; }}
        
        .table-custom {{ width: 100%; border-collapse: collapse; margin: 0; }}
        .table-custom th, .table-custom td {{ border: 1px solid black !important; }}
        .table-custom th {{ background: #e5e7eb; color: #000 !important; text-align: center; padding: 8px; font-size: 1.1rem; font-weight: normal; }}
        .table-custom td {{ padding: 8px; font-size: 1.6rem; text-align: center; line-height: 1.1; }}
        
        .table-custom .clickable-cell {{ cursor: pointer; }}
        .table-custom .clickable-cell:active {{ background-color: #fecaca !important; }}
        
        .table-custom tr.clickable-row {{ cursor: pointer; transition: background 0.1s; }}
        .table-custom tr.clickable-row:active {{ background-color: #dbeafe; }}
        .bg-blue-light {{ background-color: #e3f2fd; color: #1f2937; }}
        .bg-red-light {{ background-color: #fff1f2; color: #b91c1c; }}
        .bg-yellow {{ background-color: #fef9c3; color: #000; }}
        .text-pct-small {{ color: #000 !important; font-size: 1rem !important; font-weight: normal; }}
        .text-gray {{ color: #9ca3af; }}
        .footer-note {{ font-size: 1rem; color: #111827; text-align: center; padding: 20px; background: #f3f4f6; font-weight: normal; }}
        
        .prediction-note {{ 
            background-color: #fff; padding: 15px 20px; font-size: 1rem; color: #333; 
            text-align: center; border-top: 1px solid black; border-bottom: 1px solid black; 
            line-height: 1.3; 
        }}

        .row-empty td {{ background-color: #e9ecef; }}
        .row-total td, tfoot td {{ background-color: #d1d5db; font-weight: 900 !important; border-bottom: 1px solid black !important; }}
        .bottom-spacer {{ height: 60px; width: 100%; }}
        
        .day-header {{ display: flex; justify-content: space-between; align-items: center; width: 100%; }}
        .day-stats-row {{ display: flex; justify-content: space-between; padding: 10px 20px; font-size: 1.2rem; border-bottom: 1px solid #ddd; }}
        .day-stats-label {{ font-weight: bold; color: #555; }}
        .day-stats-val {{ font-weight: bold; color: #000; }}
        
        .col-idx {{ width: 40px; font-size: 0.9rem !important; color: #666; font-weight: normal !important; }}
        .col-nom {{ text-align: left !important; padding-left: 10px !important; font-size: 1.3rem !important; font-weight: normal !important; }}
        .col-imp {{ text-align: right !important; padding-right: 10px !important; color: #b91c1c !important; font-weight: normal !important; }}
        .col-data {{ font-size: 0.9rem !important; color: #555; width: 110px; }}
        .col-att {{ text-align: left !important; padding-left: 10px !important; font-size: 1.1rem !important; color: #555; font-weight: normal !important; }}
        .col-small {{ font-size: 0.9rem !important; width: 50px; }}

        #view-global .col-nom, #view-global .col-imp, #view-global .col-data,
        #view-customer .col-att, #view-customer .col-imp, #view-customer .col-data,
        #view-day .col-nom, #view-day .col-imp {{
            text-align: center !important;
            padding-left: 5px !important;
            padding-right: 5px !important;
        }}
        
        .row-month-change td {{ border-top: 3px solid #94a3b8 !important; background-color: #f3f4f6 !important; }}
        .th-sortable {{ cursor: pointer; user-select: none; }}
        .sort-icon {{ color: red; margin-right: 5px; font-size: 0.8em; display: none; }}
        
        .search-container {{ padding: 15px; display: flex; align-items: center; justify-content: center; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
        .search-wrapper {{ position: relative; width: 100%; max-width: 400px; }}
        .search-input {{ width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 1.1rem; padding-right: 40px; outline: none; transition: border-color 0.2s; }}
        .search-input:focus {{ border-color: #1a3b5c; box-shadow: 0 0 0 3px rgba(26, 59, 92, 0.1); }}
        .search-clear {{ position: absolute; right: 10px; top: 50%; transform: translateY(-50%); cursor: pointer; color: #ef4444; font-weight: bold; font-size: 1.2rem; display: none; padding: 5px; }}
        .search-count {{ margin-left: 10px; font-weight: bold; color: #1a3b5c; font-size: 1.1rem; white-space: nowrap; }}

        .name-link {{ cursor: pointer; color: #1a3b5c; text-decoration: underline; }}
        .dupe-box {{ margin: 15px 20px; padding: 15px; background: #fff7ed; border: 1px solid #ffedd5; border-radius: 8px; }}
        .dupe-title {{ font-size: 1rem; font-weight: bold; color: #c2410c; margin-bottom: 8px; text-transform: uppercase; }}
        .dupe-item {{ display: inline-block; background: white; padding: 5px 10px; margin: 3px; border-radius: 15px; border: 1px solid #fdba74; color: #9a3412; font-size: 0.95rem; cursor: pointer; }}
        
        @media (max-width: 480px) {{
            .table-custom td {{ padding: 8px 2px !important; font-size: 1.4rem; }}
            .table-custom th {{ padding: 8px 2px !important; }}
            .total-amount {{ font-size: 3.8rem; }}
            .bar-label-container {{ width: 85px; margin-right: 2px; }} 
            .bar-label-text {{ font-size: 0.8rem; }}
            .bar-value {{ width: 95px; font-size: 0.85rem; }}
            .progress {{ height: 18px; margin: 0 8px; }}
            
            .header-title {{ font-size: 1.3rem; }}
            .text-pct-small {{ font-size: 0.9rem !important; }}
            
            .col-idx {{ width: 25px; font-size: 0.7rem !important; padding: 2px !important; }}
            .col-nom {{ font-size: 1.1rem !important; }}
            .col-imp {{ font-size: 0.9rem !important; }}
            .col-data {{ width: 75px; font-size: 0.8rem !important; }}
            .col-att {{ font-size: 0.85rem !important; white-space: normal !important; line-height: 1.2; padding: 4px 2px !important; }}
            
            .main-wrapper {{ width: 98%; padding: 5px; }}
        }}
    </style>
</head>
<body>
<div id="loading-overlay">
    <div>Preparazione<br>PDF in corso</div>
</div>

<div id="copy-toast">Copiato!</div>

<div id="info-popup" class="popup-overlay" onclick="if(event.target===this) closePopup()">
    <div class="popup-content">
        <div class="popup-close-btn" onclick="closePopup()">&#10005;</div>
        <div id="popup-inner"></div>
    </div>
</div>

<div class="main-wrapper">
    <div id="view-home">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:80px; text-align:center;">
                    <span onclick="showGlobalList()" class="btn-user btn-styled" title="Anagrafica Globale">&#129489;</span>
                </div>
                <div style="flex-grow:1; display:flex; justify-content:space-between; align-items:center; padding: 0 5px;">
                    <div class="nav-arrow" onclick="changeView(-1)">&#10094;</div>
                    <h1 class="header-title" onclick="printCurrentView()" title="Clicca per scaricare PDF" style="cursor:pointer;">INCASSI<br>2025-26</h1>
                    <div class="nav-arrow" onclick="changeView(1)">&#10095;</div>
                </div>
                <div style="width:80px; text-align:center">
                    <span onclick="printCurrentView()" class="btn-audio btn-styled" title="Stampa PDF">🖨️</span>
                </div>
            </div>
            <div class="total-box">
                <div class="total-amount" id="home-total-display">{formatta_num(tot_annuo_proiettato)} €</div>
            </div>
            <div class="chart-section">
                <div class="bar-row" onclick="showStatsPopup()">
                    <div class="bar-label-container"><span class="bar-label-text" id="label-h-0">2024-25</span></div>
                    <div class="progress"><div class="progress-bar bg-primary" style="width: {pct_24_25}%"></div></div>
                    <span class="bar-value">{formatta_num(tot_annuo_24_25)} €</span>
                </div>
                <div class="bar-row" onclick="showStatsPopup()">
                    <div class="bar-label-container"><span class="bar-label-text" id="label-h-1">2025-26</span></div>
                    <div class="progress"><div class="progress-bar bg-danger" style="width: {pct_consuntivo}%"></div></div>
                    <span class="bar-value">{formatta_num(tot_annuo_consuntivo)} €</span>
                </div>
                <div class="bar-row" onclick="showStatsPopup()">
                    <div class="bar-label-container"><span class="bar-label-text" id="label-h-2">Previsto</span></div>
                    <div class="progress"><div class="progress-bar bg-warning" style="width: {pct_totale}%"></div></div>
                    <span class="bar-value">{formatta_num(tot_annuo_proiettato)} €</span>
                </div>
            </div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr><th>Mese</th><th>2024-25</th><th>2025-26</th><th>Previsto</th><th class="col-small">Pareggio</th></tr></thead>
                <tbody id="table-body-home"></tbody>
                <tfoot>
                    <tr class="row-total">
                        <td>Totali</td>
                        <td>{formatta_num(tot_annuo_24_25)}</td>
                        <td style="color:#b91c1c">{formatta_num(tot_annuo_consuntivo)}</td>
                        <td style="color:black">{formatta_num(tot_annuo_proiettato)}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
            <div class="prediction-note">
                Le previsioni tengono conto dell’andamento reale dell’anno, della storia degli anni passati, della stagionalità, del giorno della settimana, del momento del mese, delle chiusure, dei ponti e di una piccola variabilità naturale.
            </div>
            <div class="footer-note">Dati al {data_rif_str}</div>
        </div>
    </div>

    <div id="view-detail" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:80px; text-align:center;">
                    <a href="#" onclick="showHome(); return false;" class="btn-home btn-styled" title="Home">🏠</a>
                </div>
                <div style="flex-grow:1; display:flex; justify-content:space-between; align-items:center; padding: 0 5px;">
                    <div class="nav-arrow" onclick="changeView(-1)">&#10094;</div>
                    <h1 class="header-title" id="detail-title" style="margin:0; text-align:center; flex-grow:1; white-space:normal;">MESE<br>ANNO</h1>
                    <div class="nav-arrow" onclick="changeView(1)">&#10095;</div>
                </div>
                <div style="width:80px; text-align:center;">
                    <span onclick="printCurrentView()" class="btn-audio btn-styled" title="Stampa PDF">🖨️</span>
                </div>
            </div>
            <div class="total-box">
                <div class="total-amount" id="detail-total-display">0 €</div>
            </div>
            <div class="chart-section" id="detail-chart"></div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr>
                    <th class="col-giorno th-sortable" onclick="changeMonthSort('day')"><span id="m-icon-day" class="sort-icon"></span>Giorno</th>
                    <th class="col-val th-sortable" onclick="changeMonthSort('cons')"><span id="m-icon-cons" class="sort-icon"></span>Consuntivo</th>
                    <th class="col-val th-sortable" onclick="changeMonthSort('prev')"><span id="m-icon-prev" class="sort-icon"></span>Previsto</th>
                </tr></thead>
                <tbody id="detail-table-body"></tbody>
            </table>
            <div class="footer-note">Dati al {data_rif_str}</div>
        </div>
    </div>

    <div id="view-day" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div class="day-header">
                    <div class="nav-arrow" onclick="navDay(-1)">&#10094;</div>
                    <div class="nav-arrow-up" onclick="closeDayDetail()" title="Torna al Mese">&#9650;</div>
                    <h1 class="header-title" id="day-title" style="margin:0; font-size:1.6rem;">GIORNO<br>DATA</h1>
                    <div class="nav-arrow" onclick="navDay(1)">&#10095;</div>
                    <span onclick="printCurrentView()" class="btn-audio btn-styled" title="Stampa PDF" style="margin-left:10px;">🖨️</span>
                </div>
            </div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead>
                    <tr>
                        <th class="col-idx">#</th>
                        <th class="col-nom th-sortable" onclick="changeDaySort('nom')">
                            <span id="icon-nom" class="sort-icon"></span>Nominativo
                        </th>
                        <th class="col-imp th-sortable" onclick="changeDaySort('imp')">
                            <span id="icon-imp" class="sort-icon"></span>Importo €
                        </th>
                    </tr>
                </thead>
                <tbody id="day-table-body"></tbody>
            </table>
            <div style="background:#fff; padding:10px 0;">
                <div class="day-stats-row"><span class="day-stats-label">Totale consuntivo giorno:</span> <span class="day-stats-val" id="stats-day">0</span></div>
                <div class="day-stats-row"><span class="day-stats-label">Totale consuntivo mese:</span> <span class="day-stats-val" id="stats-month">0</span></div>
                <div class="day-stats-row"><span class="day-stats-label">Totale consuntivo anno:</span> <span class="day-stats-val" id="stats-year">0</span></div>
            </div>
        </div>
    </div>

    <div id="view-global" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:80px; text-align:center;">
                    <a href="#" onclick="showHome(); return false;" class="btn-home btn-styled" title="Home">🏠</a>
                </div>
                <div style="flex-grow:1; text-align:center;">
                    <h1 class="header-title" style="margin:0;">ANAGRAFICA<br>2025-26</h1>
                </div>
                <div style="width:80px; text-align:center;">
                    <span onclick="printCurrentView()" class="btn-audio btn-styled" title="Stampa PDF">🖨️</span>
                </div>
            </div>
            <div class="search-container">
                <div class="search-wrapper">
                    <input type="text" id="global-search" class="search-input" placeholder="Inserisci nominativo" oninput="filterGlobal(this.value)">
                    <span id="btn-clear-search" class="search-clear" onclick="clearSearch()">&#10005;</span>
                </div>
                <span id="global-filter-count" class="search-count">(0)</span>
            </div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead>
                    <tr>
                        <th class="col-idx">#</th>
                        <th class="col-data th-sortable" onclick="changeGlobalSort('data')">
                            <span id="g-icon-data" class="sort-icon"></span>Data
                        </th>
                        <th class="col-nom th-sortable" onclick="changeGlobalSort('nom')">
                            <span id="g-icon-nom" class="sort-icon"></span>Nominativo
                        </th>
                        <th class="col-imp th-sortable" onclick="changeGlobalSort('imp')">
                            <span id="g-icon-imp" class="sort-icon"></span>Importo
                        </th>
                    </tr>
                </thead>
                <tbody id="global-table-body"></tbody>
                <tfoot>
                    <tr class="row-total">
                        <td colspan="3" style="text-align:right">TOTALE:</td>
                        <td id="global-total-foot" style="color:black">0</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        <div class="bottom-spacer"></div>
    </div>

    <div id="view-customer" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:100px; display:flex; justify-content:space-between; align-items:center; padding-right:10px;">
                    <div class="nav-arrow" onclick="closeCustomer()" title="Indietro">&#10094;</div>
                    <span onclick="copyCustomerData()" class="btn-styled" title="Copia Appunti" style="font-size:1.5rem; padding:2px 8px; cursor:pointer;">📋</span>
                </div>
                <div style="flex-grow:1; text-align:center;">
                    <h1 class="header-title" id="cust-title" style="margin:0; font-size:1.8rem; white-space:normal;">CLIENTE</h1>
                </div>
                <div style="width:80px; text-align:center;">
                    <span onclick="printCurrentView()" class="btn-audio btn-styled" title="Stampa PDF">🖨️</span>
                </div>
            </div>
        </div>
        
        <div id="cust-duplicates" class="dupe-box" style="display:none;">
            <div class="dupe-title">Possibili duplicati:</div>
            <div id="dupe-list"></div>
        </div>

        <div class="card-box">
            <table class="table-custom">
                <thead>
                    <tr>
                        <th class="col-idx">#</th>
                        <th class="col-data th-sortable" onclick="changeCustSort('data')">
                            <span id="c-icon-data" class="sort-icon"></span>Data
                        </th>
                        <th class="col-att th-sortable" onclick="changeCustSort('att')">
                            <span id="c-icon-att" class="sort-icon"></span>Attività
                        </th>
                        <th class="col-imp th-sortable" onclick="changeCustSort('imp')">
                            <span id="c-icon-imp" class="sort-icon"></span>Importo
                        </th>
                    </tr>
                </thead>
                <tbody id="cust-table-body"></tbody>
                <tfoot>
                    <tr class="row-total">
                        <td colspan="3" style="text-align:right">TOTALE:</td>
                        <td id="cust-total-foot" style="color:black">0</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        <div class="bottom-spacer"></div>
    </div>

    <div class="bottom-spacer"></div>
</div>

<script>
    const dati = {json.dumps(json_data)};
    const mesiOrdine = {json.dumps(MESI_ORDINE)};
    const isAdmin = {js_admin_flag};
    const globalIndex = dati.GLOBAL_DAY_INDEX; 
    let viewIndex = 12; 
    let currentMese = null;
    let currentDayNum = 0;
    let lastView = 'view-home'; 
    let globalScrollPos = 0; 
    let sortCol = 'nom'; let sortDir = 'asc'; 
    let gSortCol = 'nom'; let gSortDir = 'asc';
    let globalSearchTerm = "";
    
    // CUSTOMER SORT VARS
    let custSortCol = 'data'; let custSortDir = 'desc'; 
    let currentCustName = "";
    let currentCustTransactions = []; 
    let monthSortCol = 'day'; let monthSortDir = 'asc'; 

    const BASE_API = "https://countapi.mileshilliard.com/api/v1";
    const NAMESPACE = "joyfit-stats-v1";
    
    function trackVisit(pageKey) {{
        if (isAdmin) return;
        fetch(`${{BASE_API}}/hit/${{NAMESPACE}}_${{pageKey}}`, {{ mode: 'cors' }}).catch(e => {{}});
    }}

    const fmt = (n) => n > 0 ? Math.round(n).toString().replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ".") : "";
    const fmtFull = (n) => n >= 0 ? Math.round(n).toString().replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ".") : "0";

    const homeValues = ["{formatta_num(tot_annuo_proiettato)} €", "{formatta_num(tot_annuo_24_25)} €", "{formatta_num(tot_annuo_consuntivo)} €"];
    let detailValues = ["0 €", "0 €", "0 €"];
    const mapValIndexToLabelId = [2, 0, 1];
    const textColors = ['#d97706', '#0d6efd', '#dc3545']; 
    let valIndex = 0; 
    let idleTimer;
    let rotationInterval;

    function getTimestampFilename() {{
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const y = now.getFullYear();
        const m = pad(now.getMonth() + 1);
        const d = pad(now.getDate());
        const h = pad(now.getHours());
        const min = pad(now.getMinutes());
        const s = pad(now.getSeconds());
        return `${{y}}-${{m}}-${{d}}-${{h}}-${{min}}-${{s}}.pdf`;
    }}

    async function printCurrentView() {{
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = 'flex';

        setTimeout(async () => {{
            try {{
                const views = ['view-home', 'view-detail', 'view-day', 'view-global', 'view-customer'];
                let targetId = views.find(id => document.getElementById(id).style.display !== 'none');
                const {{ jsPDF }} = window.jspdf;
                const doc = new jsPDF('p', 'mm', 'a4');
                const filename = getTimestampFilename();
                
                if (targetId === 'view-global') {{
                    const searchTerm = document.getElementById('global-search').value.toLowerCase();
                    let filteredList = [];
                    if (searchTerm) filteredList = dati.GLOBAL_LIST.filter(item => item.nome.toLowerCase().includes(searchTerm));
                    else filteredList = dati.GLOBAL_LIST;
                    
                    if (filteredList.length > 50) {{
                        alert("Troppi righi (" + filteredList.length + "). Massimo 50 per la stampa.");
                        overlay.style.display = 'none';
                        return;
                    }}
                }}

                if (!targetId) {{ overlay.style.display = 'none'; return; }}
                const element = document.getElementById(targetId);
                
                // COMPRESSION: JPEG with 0.65 quality
                const canvas = await html2canvas(element, {{ scale: 2, useCORS: true }});
                const imgData = canvas.toDataURL('image/jpeg', 0.65);
                
                const pageWidth = 210;
                const pageHeight = 297;
                const margin = 15; 
                const maxW = pageWidth - (margin * 2);
                const maxH = pageHeight - (margin * 2);
                
                const imgProps = doc.getImageProperties(imgData);
                let pdfWidth = maxW;
                let pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
                
                if (pdfHeight > maxH) {{
                    const scale = maxH / pdfHeight;
                    pdfWidth = pdfWidth * scale;
                    pdfHeight = pdfHeight * scale;
                }}
                
                doc.addImage(imgData, 'JPEG', margin + (maxW - pdfWidth) / 2, margin, pdfWidth, pdfHeight);
                
                doc.save(filename); 
                
                const blobUrl = doc.output('bloburl');
                window.open(blobUrl, '_blank');

            }} catch (e) {{
                alert("Errore stampa: " + e);
            }} finally {{
                overlay.style.display = 'none';
            }}
        }}, 50);
    }}

    function clearHighlights() {{
        ['label-h-0','label-h-1','label-h-2','label-d-0','label-d-1','label-d-2'].forEach(id => {{
            const el = document.getElementById(id);
            if(el) el.style.borderColor = 'transparent';
        }});
    }}

    function applyHighlight(labelSuffix, colorIndex) {{
        const el = document.getElementById('label-' + labelSuffix + '-' + mapValIndexToLabelId[colorIndex]);
        if(el) el.style.border = "4px solid " + textColors[colorIndex];
    }}

    function showValue(index) {{
        clearHighlights();
        const isHome = (document.getElementById('view-home').style.display !== 'none');
        if (document.getElementById('view-day').style.display !== 'none' || document.getElementById('view-global').style.display !== 'none' || document.getElementById('view-customer').style.display !== 'none') return; 

        const suffix = isHome ? 'h' : 'd';
        applyHighlight(suffix, index);
        const targetId = isHome ? 'home-total-display' : 'detail-total-display';
        const vals = isHome ? homeValues : detailValues;
        
        const disp = document.getElementById(targetId);
        if(disp) {{
            disp.style.opacity = 0;
            setTimeout(() => {{
                disp.innerText = vals[index];
                disp.style.color = textColors[index];
                disp.style.opacity = 1;
            }}, 500);
        }}
    }}

    function nextScreen() {{ valIndex = (valIndex + 1) % 3; showValue(valIndex); }}
    function startScreensaver() {{ 
        if (document.getElementById('view-day').style.display !== 'none' || document.getElementById('view-global').style.display !== 'none' || document.getElementById('view-customer').style.display !== 'none') return;
        nextScreen(); 
        rotationInterval = setInterval(nextScreen, 10000); 
    }}
    
    function resetIdle() {{
        clearInterval(rotationInterval);
        rotationInterval = null;
        clearTimeout(idleTimer);
        valIndex = 0;
        clearHighlights();
        
        const isHome = (document.getElementById('view-home').style.display !== 'none');
        if (isHome) {{
            applyHighlight('h', 0);
            const d = document.getElementById('home-total-display');
            if(d) {{ d.innerText = homeValues[0]; d.style.color = textColors[0]; d.style.opacity = 1; }}
        }} else if (document.getElementById('view-detail').style.display !== 'none') {{
            applyHighlight('d', 0);
            const d = document.getElementById('detail-total-display');
            if(d) {{ d.innerText = detailValues[0]; d.style.color = textColors[0]; d.style.opacity = 1; }}
        }}
        idleTimer = setTimeout(startScreensaver, 10000); 
    }}

    ['mousemove', 'mousedown', 'touchstart', 'click', 'keydown', 'scroll'].forEach(evt => document.addEventListener(evt, resetIdle));
    
    document.addEventListener('keydown', function(event) {{
        if (event.key === 'ArrowLeft') changeView(-1);
        else if (event.key === 'ArrowRight') changeView(1);
        else if (event.key === 'Escape') showHome();
    }});

    let touchStartX=0, touchStartY=0;
    document.addEventListener('touchstart', e => {{ touchStartX=e.changedTouches[0].screenX; touchStartY=e.changedTouches[0].screenY; }}, {{passive:false}});
    
    document.addEventListener('touchend', e => {{
        let xDiff = e.changedTouches[0].screenX - touchStartX;
        let yDiff = e.changedTouches[0].screenY - touchStartY;
        if (Math.abs(xDiff) > Math.abs(yDiff)) {{ 
            if (Math.abs(xDiff)>50) changeView(xDiff>0 ? -1 : 1); 
        }}
    }}, {{passive:false}});

    // --- POPUP LOGIC ---
    function showStatsPopup(monthKey) {{
        let ref, cons, prev, dataRif, timeline = false;
        let breakeven = null;
        let popupTitle = "";
        let labelRef = "";
        let prevYear = "";

        // Se monthKey è undefined/null, usiamo i dati globali (Home)
        if (!monthKey) {{
            const s = dati.GLOBAL_STATS;
            if(!s) return;
            ref = s.tot_ref;
            cons = s.tot_cons;
            prev = s.tot_prev;
            dataRif = s.data_rif;
            timeline = true; 
            popupTitle = "RIEPILOGO STAGIONE";
            labelRef = "STAGIONE 2024-25";
        }} else {{
            const m = dati[monthKey];
            if(!m) return;
            ref = m.tot_24_25;
            cons = m.tot_cons;
            prev = m.tot_full;
            dataRif = dati.GLOBAL_STATS.data_rif;
            timeline = false;
            if (m.breakeven) breakeven = m.breakeven;
            popupTitle = m.title_mese + " " + m.title_anno;
            prevYear = parseInt(m.title_anno) - 1;
            labelRef = m.title_mese + " " + prevYear;
        }}
        
        const safeRef = ref > 0 ? ref : 1; 
        
        const diffCons = cons - ref;
        const diffPrev = prev - ref;
        
        const pctCons = (diffCons / safeRef) * 100;
        const pctPrev = (diffPrev / safeRef) * 100;
        
        const missingCons = ref - cons; 
        const missingPrev = prev - cons; 
        
        // CALCOLO DATA PAREGGIO (Solo Globale se timeline active)
        if (timeline && prev >= ref && dati.FORECAST_TIMELINE) {{
            const refDateParts = dataRif.split('/');
            const refDateObj = new Date(refDateParts[2], parseInt(refDateParts[1])-1, refDateParts[0]);
            const refTs = refDateObj.getTime() / 1000;
            
            let runningTotal = cons;
            for (let day of dati.FORECAST_TIMELINE) {{
                if (day.ts <= refTs) continue; 
                runningTotal += day.val;
                if (runningTotal >= ref) {{
                    breakeven = day.date;
                    break;
                }}
            }}
        }}

        const fmtPct = (p) => {{
             let sign = p >= 0 ? "+" : "";
             return `(${{sign}}${{p.toFixed(1).replace('.', ',')}}%)`;
        }};
        
        const html = `
            <div class="popup-header">${{popupTitle}}</div>
            <div class="popup-row">
                <div class="popup-label">${{labelRef}}</div>
                <div class="popup-val" style="color:#0d6efd">${{fmtFull(ref)}} €</div>
            </div>
            
            <div class="popup-row">
                <div class="popup-label">CONSUNTIVO</div>
                <div class="popup-val" style="color:#b91c1c">
                    ${{fmtFull(cons)}} € 
                    <span class="popup-diff" style="color:#b91c1c">${{fmtPct(pctCons)}}</span>
                </div>
                ${{ breakeven ? `<div class="popup-breakeven">Pareggio ${{breakeven}}</div>` : '' }}
                ${{ missingCons > 0 ? `<div class="popup-missing">Mancano ${{fmtFull(missingCons)}} €</div>` : '' }}
            </div>
            
            <div class="popup-row">
                <div class="popup-label">Previsto / Totale</div>
                <div class="popup-val" style="color:#d97706">
                    ${{fmtFull(prev)}} €
                    <span class="popup-diff" style="color:#d97706">${{fmtPct(pctPrev)}}</span>
                </div>
                ${{ missingPrev > 0 ? `<div class="popup-missing">Mancano ${{fmtFull(missingPrev)}} €</div>` : '' }}
            </div>
        `;
        
        document.getElementById('popup-inner').innerHTML = html;
        document.getElementById('info-popup').style.display = 'flex';
    }}
    
    function closePopup() {{
        document.getElementById('info-popup').style.display = 'none';
    }}

    function initHome() {{
        const tbody = document.getElementById('table-body-home');
        tbody.innerHTML = '';
        mesiOrdine.forEach((mese, index) => {{
            const d = dati[mese];
            const row = document.createElement('tr');
            row.className = 'clickable-row';
            row.onclick = () => {{ viewIndex = index; showDetail(mese); }};
            row.innerHTML = `<td>${{mese}}</td><td class="bg-blue-light">${{d.home_data.old}}</td><td class="${{d.home_data.cons?'bg-red-light':'text-gray'}}">${{d.home_data.cons}}</td><td class="${{d.home_data.prev_style}}">${{d.home_data.prev_txt}}</td><td class="col-small" style="font-size:0.9em">${{d.breakeven || ""}}</td>`;
            tbody.appendChild(row);
        }});
        trackVisit('report_home');
        resetIdle();
    }}

    function changeView(direction) {{
        const totalStates = mesiOrdine.length + 1;
        viewIndex = (viewIndex + direction + totalStates) % totalStates;
        if (viewIndex === mesiOrdine.length) showHome(); else showDetail(mesiOrdine[viewIndex]);
        resetIdle();
    }}

    function showHome() {{
        document.querySelectorAll('.main-wrapper > div').forEach(d => d.style.display = 'none');
        document.getElementById('view-home').style.display = 'block';
        lastView = 'view-home';
        viewIndex = 12; 
        window.scrollTo(0,0);
        resetIdle();
    }}

    function changeMonthSort(col) {{
        if (monthSortCol === col) monthSortDir = (monthSortDir === 'asc') ? 'desc' : 'asc';
        else {{ monthSortCol = col; monthSortDir = 'asc'; }} 
        showDetail(currentMese);
    }}

    function showDetail(mese) {{
        currentMese = mese;
        viewIndex = mesiOrdine.indexOf(mese);
        const d = dati[mese];
        document.getElementById('detail-title').innerHTML = d.title_mese + "<br>" + d.title_anno;
        trackVisit('report_' + mese);
        detailValues = [fmtFull(d.tot_full) + ' €', fmtFull(d.tot_24_25) + ' €', fmtFull(d.tot_cons) + ' €'];
        document.getElementById('detail-total-display').innerText = detailValues[0];
        const maxVal = Math.max(d.tot_24_25, d.tot_full) || 1;
        const pOld = (d.tot_24_25 / maxVal) * 100;
        const pCons = (d.tot_cons / maxVal) * 100;
        const pFull = (d.tot_full / maxVal) * 100;
        
        document.getElementById('detail-chart').innerHTML = `
            <div class="bar-row" onclick="showStatsPopup('${{mese}}')"><div class="bar-label-container"><span class="bar-label-text" id="label-d-0">2024-25</span></div><div class="progress"><div class="progress-bar bg-primary" style="width: ${{pOld}}%"></div></div><span class="bar-value">${{fmtFull(d.tot_24_25)}} €</span></div>
            <div class="bar-row" onclick="showStatsPopup('${{mese}}')"><div class="bar-label-container"><span class="bar-label-text" id="label-d-1">2025-26</span></div><div class="progress"><div class="progress-bar bg-danger" style="width: ${{pCons}}%"></div></div><span class="bar-value">${{fmtFull(d.tot_cons)}} €</span></div>
            <div class="bar-row" onclick="showStatsPopup('${{mese}}')"><div class="bar-label-container"><span class="bar-label-text" id="label-d-2">Previsto</span></div><div class="progress"><div class="progress-bar bg-warning" style="width: ${{pFull}}%"></div></div><span class="bar-value">${{fmtFull(d.tot_full)}} €</span></div>
        `;

        const tbody = document.getElementById('detail-table-body');
        tbody.innerHTML = '';
        let list = [...d.lista_giorni];
        list.sort((a,b) => {{
            let valA, valB;
            if (monthSortCol === 'day') {{ valA = a.day_num; valB = b.day_num; }}
            else if (monthSortCol === 'cons') {{ valA = a.cons; valB = b.cons; }}
            else if (monthSortCol === 'prev') {{ valA = a.prev; valB = b.prev; }}
            return (monthSortDir === 'asc') ? (valA - valB) : (valB - valA);
        }});
        ['day', 'cons', 'prev'].forEach(k => document.getElementById('m-icon-'+k).style.display = 'none');
        const activeIcon = document.getElementById('m-icon-' + monthSortCol);
        activeIcon.style.display = 'inline';
        activeIcon.innerHTML = (monthSortDir === 'asc') ? '&#9660;' : '&#9650;';

        if(list.length > 0) {{
            list.forEach(day => {{
                const r = document.createElement('tr');
                r.id = 'row-day-' + day.day_num;
                if (day.cons == 0 && day.prev == 0) r.className = 'row-empty';
                
                let consCell = `<td class="col-val text-gray">${{fmt(day.cons)}}</td>`;
                if (day.cons > 0) consCell = `<td class="col-val bg-red-light clickable-cell" onclick="showDay('${{mese}}', '${{day.day_num}}')">${{fmt(day.cons)}}</td>`;
                
                r.innerHTML = `<td class="col-giorno">${{day.giorno}}</td>${{consCell}}<td class="col-val ${{day.prev?'bg-yellow':''}}">${{fmt(day.prev)}}</td>`;
                tbody.appendChild(r);
            }});
        }}
        const tRow = document.createElement('tr');
        tRow.className = 'row-total clickable-row';
        tRow.onclick = () => showStatsPopup(mese);
        tRow.innerHTML = `<td>TOT</td><td style="color:black">${{fmtFull(d.tot_cons)}}</td><td style="color:black">${{fmtFull(d.tot_prev)}}</td>`;
        tbody.appendChild(tRow);
        document.querySelectorAll('.main-wrapper > div').forEach(d => d.style.display = 'none');
        document.getElementById('view-detail').style.display = 'block';
        lastView = 'view-detail';
        window.scrollTo(0,0);
        resetIdle();
    }}

    function changeDaySort(col) {{
        if (sortCol === col) sortDir = (sortDir === 'asc') ? 'desc' : 'asc';
        else {{ sortCol = col; sortDir = (col === 'nom') ? 'asc' : 'desc'; }}
        showDay(currentMese, currentDayNum);
    }}

    function showDay(mese, dayNum) {{
        const details = dati[mese].dettagli[dayNum];
        if (!details) {{ alert("Nessun dettaglio trovato."); return; }}
        currentMese = mese; currentDayNum = parseInt(dayNum);
        document.getElementById('day-title').innerHTML = details.title_day_name + "<br>" + details.title_date;
        const tbody = document.getElementById('day-table-body');
        tbody.innerHTML = '';
        let transSorted = [...details.trans];
        if (sortCol === 'nom') {{
            transSorted.sort((a, b) => {{
                let va = a.nome.toLowerCase(), vb = b.nome.toLowerCase();
                if (va < vb) return (sortDir === 'asc' ? -1 : 1);
                if (va > vb) return (sortDir === 'asc' ? 1 : -1);
                return 0;
            }});
        }} else {{
            transSorted.sort((a, b) => (sortDir === 'asc') ? (a.imp - b.imp) : (b.imp - a.imp));
        }}
        document.getElementById('icon-nom').style.display = 'none';
        document.getElementById('icon-imp').style.display = 'none';
        const activeIcon = document.getElementById('icon-' + sortCol);
        activeIcon.style.display = 'inline';
        activeIcon.innerHTML = (sortCol === 'nom') ? (sortDir === 'asc' ? '&#9660;' : '&#9650;') : (sortDir === 'desc' ? '&#9660;' : '&#9650;');
        transSorted.forEach((t, i) => {{
            const isDupe = dati.DUPLICATES_MAP[t.nome] && dati.DUPLICATES_MAP[t.nome].length > 0;
            const colorStyle = isDupe ? "color: #0044cc !important; font-weight:bold;" : ""; 
            const r = document.createElement('tr');
            r.innerHTML = `<td class="col-idx">${{i+1}}</td><td class="col-nom name-link" style="${{colorStyle}}" onclick="showCustomer('${{t.nome}}')">${{t.nome}}</td><td class="col-imp">${{fmt(t.imp)}}</td>`;
            tbody.appendChild(r);
        }});
        document.getElementById('stats-day').innerText = fmtFull(details.tot_day);
        document.getElementById('stats-month').innerText = fmtFull(dati[mese].tot_cons);
        document.getElementById('stats-year').innerText = fmtFull(dati["GLOBAL_STATS"].tot_annuo);
        document.querySelectorAll('.main-wrapper > div').forEach(d => d.style.display = 'none');
        document.getElementById('view-day').style.display = 'block';
        lastView = 'view-day';
        window.scrollTo(0,0);
        trackVisit('report_' + mese + '_day');
        resetIdle(); 
    }}

    function closeDayDetail() {{ 
        showDetail(currentMese); 
        setTimeout(() => {{
            const el = document.getElementById('row-day-' + currentDayNum);
            if(el) el.scrollIntoView({{behavior: 'auto', block: 'center'}});
        }}, 50);
    }}
    
    function navDay(dir) {{
        let currIdx = -1;
        for(let i=0; i<globalIndex.length; i++) {{ if(globalIndex[i].m === currentMese && globalIndex[i].d === currentDayNum) {{ currIdx = i; break; }} }}
        if (currIdx !== -1) {{
            let newIdx = currIdx + dir;
            if (newIdx >= 0 && newIdx < globalIndex.length) {{ let target = globalIndex[newIdx]; showDay(target.m, target.d); }}
        }}
    }}

    function showGlobalList() {{
        document.querySelectorAll('.main-wrapper > div').forEach(d => d.style.display = 'none');
        document.getElementById('view-global').style.display = 'block';
        lastView = 'view-global';
        gSortCol = 'nom'; gSortDir = 'asc'; globalSearchTerm = "";
        document.getElementById('global-search').value = "";
        renderGlobal();
        trackVisit('report_global_list');
    }}

    function changeGlobalSort(col) {{
        if (gSortCol === col) gSortDir = (gSortDir === 'asc') ? 'desc' : 'asc';
        else {{ gSortCol = col; gSortDir = (col === 'nom') ? 'asc' : 'desc'; }}
        renderGlobal();
    }}

    function filterGlobal(val) {{ globalSearchTerm = val.toLowerCase(); renderGlobal(); }}
    function clearSearch() {{ document.getElementById('global-search').value = ""; filterGlobal(""); }}

    function renderGlobal() {{
        let list = [...dati.GLOBAL_LIST];
        if (globalSearchTerm) list = list.filter(item => item.nome.toLowerCase().includes(globalSearchTerm));
        document.getElementById('btn-clear-search').style.display = globalSearchTerm ? 'block' : 'none';
        document.getElementById('global-filter-count').innerText = "(" + list.length + ")";
        let filteredTotal = list.reduce((sum, item) => sum + item.imp, 0);
        document.getElementById('global-total-foot').innerText = fmtFull(filteredTotal);
        const tbody = document.getElementById('global-table-body');
        tbody.innerHTML = '';
        list.sort((a, b) => {{
            if (gSortCol === 'nom') {{
                let va = a.nome.toLowerCase(), vb = b.nome.toLowerCase();
                if (va < vb) return (gSortDir === 'asc' ? -1 : 1);
                if (va > vb) return (gSortDir === 'asc' ? 1 : -1);
                return 0;
            }} else if (gSortCol === 'imp') {{
                return (gSortDir === 'asc') ? (a.imp - b.imp) : (b.imp - a.imp);
            }} else if (gSortCol === 'data') {{
                return (gSortDir === 'asc') ? (a.ts - b.ts) : (b.ts - a.ts);
            }}
        }});
        ['data', 'nom', 'imp'].forEach(k => document.getElementById('g-icon-'+k).style.display = 'none');
        const activeIcon = document.getElementById('g-icon-' + gSortCol);
        activeIcon.style.display = 'inline';
        let arrow = '';
        if (gSortCol === 'nom') arrow = (gSortDir === 'asc') ? '&#9660;' : '&#9650;';
        else arrow = (gSortDir === 'desc') ? '&#9660;' : '&#9650;';
        activeIcon.innerHTML = arrow;
        let lastMonth = "";
        list.forEach((t, i) => {{
            const currentMonth = t.last_date.substring(3, 10);
            let rowClass = "";
            if (i > 0 && currentMonth !== lastMonth) rowClass = "row-month-change";
            lastMonth = currentMonth;
            const isDupe = dati.DUPLICATES_MAP[t.nome] && dati.DUPLICATES_MAP[t.nome].length > 0;
            const colorStyle = isDupe ? "color: #0044cc !important; font-weight:bold;" : ""; 
            const r = document.createElement('tr');
            if(rowClass) r.className = rowClass;
            r.innerHTML = `<td class="col-idx">${{i+1}}</td><td class="col-data">${{t.last_date}}</td><td class="col-nom name-link" style="${{colorStyle}}" onclick="showCustomer('${{t.nome}}')">${{t.nome}}</td><td class="col-imp">${{fmt(t.imp)}}</td>`;
            tbody.appendChild(r);
        }});
    }}

    function changeCustSort(col) {{
        if (custSortCol === col) {{
            custSortDir = (custSortDir === 'asc') ? 'desc' : 'asc';
        }} else {{
            custSortCol = col;
            // Default sort direction logic: 
            // - Date: DESC (Newest first)
            // - Imp: DESC (Highest first)
            // - Att: ASC (A-Z)
            if (col === 'data' || col === 'imp') custSortDir = 'desc';
            else custSortDir = 'asc';
        }}
        showCustomer(currentCustName);
    }}

    function showCustomer(name) {{
        if (document.getElementById('view-global').style.display !== 'none') {{
            globalScrollPos = window.scrollY;
        }}

        currentCustName = name;
        document.getElementById('cust-title').innerText = name;
        
        // Reset sort only if view was closed (actually standardizing on global vars is better)
        if(document.getElementById('view-customer').style.display === 'none') {{ 
            custSortCol = 'data'; 
            custSortDir = 'desc'; 
        }}
        
        const dupeList = dati.DUPLICATES_MAP[name];
        const dupeContainer = document.getElementById('cust-duplicates');
        const dupeListEl = document.getElementById('dupe-list');
        dupeListEl.innerHTML = '';
        if (dupeList && dupeList.length > 0) {{
            dupeContainer.style.display = 'block';
            dupeList.forEach(d => {{
                let span = document.createElement('span');
                span.className = 'dupe-item';
                span.innerText = d;
                span.onclick = () => showCustomer(d); 
                dupeListEl.appendChild(span);
            }});
        }} else {{
            dupeContainer.style.display = 'none';
        }}
        
        let transactions = dati.ALL_TRANSACTIONS.filter(t => t.nome === name);
        
        transactions.sort((a, b) => {{
            if (custSortCol === 'data') {{
                return (custSortDir === 'asc') ? (a.ts - b.ts) : (b.ts - a.ts);
            }} else if (custSortCol === 'imp') {{
                return (custSortDir === 'asc') ? (a.imp - b.imp) : (b.imp - a.imp);
            }} else if (custSortCol === 'att') {{
                const sA = (a.att || "").toString().toLowerCase();
                const sB = (b.att || "").toString().toLowerCase();
                if (sA < sB) return (custSortDir === 'asc' ? -1 : 1);
                if (sA > sB) return (custSortDir === 'asc' ? 1 : -1);
                return 0;
            }}
            return 0;
        }});
        
        currentCustTransactions = transactions; 
        
        ['data', 'att', 'imp'].forEach(k => document.getElementById('c-icon-'+k).style.display = 'none');
        const activeIcon = document.getElementById('c-icon-' + custSortCol);
        if(activeIcon) {{
            activeIcon.style.display = 'inline';
            let arrow = '';
            // Visual feedback: usually up arrow = ascending (A-Z, 0-9), down = descending
            if (custSortDir === 'asc') arrow = '&#9660;'; // Down (A at top, Z at bottom) - wait, conventional is small-to-large
            else arrow = '&#9650;'; 
            
            // Actually, let's use standard convention:
            // ASC (Small -> Large) = Up Triangle? Or Down?
            // Let's stick to what we used in Global: 
            // nom (ASC) = Down Arrow (A top, Z bottom)
            if (custSortDir === 'asc') arrow = '&#9660;'; 
            else arrow = '&#9650;'; 
            
            activeIcon.innerHTML = arrow;
        }}

        const tbody = document.getElementById('cust-table-body');
        tbody.innerHTML = '';
        let total = 0;
        transactions.forEach((t, i) => {{
            total += t.imp;
            const r = document.createElement('tr');
            r.innerHTML = `<td class="col-idx">${{i+1}}</td><td class="col-data">${{t.date_str}}</td><td class="col-att">${{t.att}}</td><td class="col-imp">${{fmt(t.imp)}}</td>`;
            tbody.appendChild(r);
        }});
        document.getElementById('cust-total-foot').innerText = fmtFull(total);
        document.querySelectorAll('.main-wrapper > div').forEach(d => d.style.display = 'none');
        document.getElementById('view-customer').style.display = 'block';
        window.scrollTo(0,0);
        trackVisit('report_cust_detail');
    }}
    
    function copyCustomerData() {{
        if (!currentCustTransactions || currentCustTransactions.length === 0) return;
        
        let totalVal = currentCustTransactions.reduce((acc, t) => acc + t.imp, 0);
        let totalStr = fmt(totalVal);
        
        let text = currentCustName.toUpperCase() + " (" + totalStr + " €)\\n";
        text += "-----\\n";
        
        currentCustTransactions.forEach(t => {{
            let attStr = t.att ? t.att : "...";
            let impStr = fmt(t.imp);
            text += `${{t.date_str}} ${{attStr}} (${{impStr}} €)\\n`;
        }});
        
        text += "-----\\n\\n"; // DOUBLE NEWLINE AT END
        
        if (navigator.clipboard) {{
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('copy-toast');
                toast.style.display = 'block';
                setTimeout(() => {{ toast.style.display = 'none'; }}, 1000);
            }}).catch(err => {{
                alert("Errore copia.");
            }});
        }} else {{
            alert("Copia non supportata su questo browser.");
        }}
    }}

    function closeCustomer() {{
        document.getElementById('view-customer').style.display = 'none';
        if(lastView && document.getElementById(lastView)) {{
            document.getElementById(lastView).style.display = 'block';
            if (lastView === 'view-global') {{
                 setTimeout(() => window.scrollTo(0, globalScrollPos), 10);
            }}
        }} else {{
            showHome();
        }}
    }}

    initHome();
</script>
</body>
</html>
"""
    return html

# --- 3. DASHBOARD CONTATORI ---
def genera_html_conta():
    html = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<title>Monitor Report</title>
<style>
  :root{ --ink: #0f172a; --bg: #e9edf5; --blue: #2563eb; --rad: 12px; --danger: #dc2626; --danger-dark: #b91c1c; }
  * { box-sizing: border-box; }
  body{ margin: 0; padding: 10px; font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--ink); font-size: 20px; display: flex; justify-content: center; }
  .box{ background: #fff; border-radius: var(--rad); padding: 20px; width: 100%; max-width: 600px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
  h1{ text-align: center; color: #1F497D; margin: 5px 0 20px 0; font-size: 1.5em; text-transform: uppercase; }
  .btn-reset-all { display: block; width: 100%; padding: 15px; margin-bottom: 20px; background-color: var(--danger); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 800; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 6px rgba(220, 38, 38, 0.3); transition: background 0.2s; }
  .btn-reset-all:hover { background-color: var(--danger-dark); }
  .btn-reset-all:active { transform: translateY(2px); }
  table{ width: 100%; border-collapse: collapse; }
  th, td{ padding: 12px 8px; border-bottom: 1px solid #f1f5f9; text-align: left; }
  th{ background: #f8fafc; color: #64748b; font-size: 0.75em; text-transform: uppercase; }
  .num{ font-weight: 800; color: var(--blue); float: right; font-size: 1.1em; }
  .btn-reset { background: #fff; border: 2px solid #e2e8f0; color: #94a3b8; border-radius: 6px; cursor: pointer; padding: 4px 12px; font-weight: 700; font-size: 0.8em; float: right; transition: all 0.2s; }
  .btn-reset:hover { background: var(--danger); color: #fff; border-color: var(--danger); }
</style>
</head>
<body>
<div class="box">
  <h1>📊 Monitor Report</h1>
  <button class="btn-reset-all" onclick="resetAllCounts()">🗑️ AZZERA TUTTO</button>
  <table id="tbl">
    <thead><tr><th width="50%">Pagina</th><th width="30%" style="text-align:right">Visite</th><th width="20%"></th></tr></thead>
    <tbody><tr><td colspan="3" style="text-align:center; padding:20px;">Caricamento...</td></tr></tbody>
  </table>
</div>
<script>
const NAMESPACE = "joyfit-stats-v1"; 
const BASE_URL = "https://countapi.mileshilliard.com/api/v1";
const PAGES = [
  { id: 'report_home', name: "🏠 Home Report" },
  { id: 'report_SET', name: "Settembre" }, { id: 'report_OTT', name: "Ottobre" }, { id: 'report_NOV', name: "Novembre" },
  { id: 'report_DIC', name: "Dicembre" }, { id: 'report_GEN', name: "Gennaio" }, { id: 'report_FEB', name: "Febbraio" },
  { id: 'report_MAR', name: "Marzo" }, { id: 'report_APR', name: "Aprile" }, { id: 'report_MAG', name: "Maggio" },
  { id: 'report_GIU', name: "Giugno" }, { id: 'report_LUG', name: "Luglio" }, { id: 'report_AGO', name: "Agosto" },
  { id: 'report_global_list', name: "👤 Anagrafica" },
  { id: 'report_cust_detail', name: "📋 Scheda Cliente" }
];
async function loadCounts() {
    const tbody = document.querySelector("#tbl tbody");
    let html = "";
    const promises = PAGES.map(async p => {
        let val = 0;
        try { let res = await fetch(`${BASE_URL}/get/${NAMESPACE}_${p.id}`); let data = await res.json(); val = data.value || 0; } catch(e){}
        return { ...p, val };
    });
    const results = await Promise.all(promises);
    for(let item of results) {
        const rowStyle = item.val > 0 ? "background-color:#f0f9ff;" : "";
        const numStyle = item.val > 0 ? "color:#0d6efd;" : "color:#ccc;";
        const btnStyle = item.val > 0 ? "border-color:#dc2626; color:#dc2626;" : "";
        html += `<tr style="${rowStyle}"><td>${item.name}</td><td><span class="num" style="${numStyle}">${item.val}</span></td><td><button class="btn-reset" style="${btnStyle}" onclick="resetCount('${item.id}')">X</button></td></tr>`;
    }
    tbody.innerHTML = html;
}
async function resetCount(id) {
    if(!confirm("Vuoi azzerare questo contatore?")) return;
    try { await fetch(`${BASE_URL}/set/${NAMESPACE}_${id}?value=0`); loadCounts(); } catch(e) { alert("Errore connessione"); }
}
async function resetAllCounts() {
    if(!confirm("ATTENZIONE: Stai per cancellare TUTTI i dati delle visite.\\n\\nSei sicuro?")) return;
    const btn = document.querySelector(".btn-reset-all");
    const originalText = btn.innerText;
    btn.innerText = "⏳ CANCELLAZIONE...";
    btn.disabled = true;
    const promises = PAGES.map(p => fetch(`${BASE_URL}/set/${NAMESPACE}_${p.id}?value=0`).catch(e => e));
    try { await Promise.all(promises); await loadCounts(); } catch (e) { alert("Errore"); loadCounts(); } finally { btn.innerText = originalText; btn.disabled = false; }
}
loadCounts();
setInterval(loadCounts, 5000);
</script>
</body>
</html>"""
    return html

def genera_app():
    print("Elaborazione report...")
    dati_mensili, dati_giornalieri = estrai_dati_completi(INPUT_PDF_URL)
    dati_transazioni, all_transactions, dupe_map = carica_dati_csv(INPUT_CSV_FILE)
    data_rif = leggi_data_da_file_txt(INPUT_DATE_FILE)
    if not data_rif: data_rif = "20/12/2025"

    html_public = genera_html_report(dati_mensili, dati_giornalieri, dati_transazioni, all_transactions, dupe_map, data_rif, is_admin_version=False)
    html_admin = genera_html_report(dati_mensili, dati_giornalieri, dati_transazioni, all_transactions, dupe_map, data_rif, is_admin_version=True)
    html_conta = genera_html_conta()
    
    try:
        if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        
        with open(OUTPUT_REPORT, "w", encoding="utf-8") as f: f.write(html_public)
        print(f"Creato: {OUTPUT_REPORT}")
        
        with open(OUTPUT_ADMIN, "w", encoding="utf-8") as f: f.write(html_admin)
        print(f"Creato: {OUTPUT_ADMIN}")
        
        with open(OUTPUT_CONTA, "w", encoding="utf-8") as f: f.write(html_conta)
        print(f"Creato: {OUTPUT_CONTA}")
        
        if os.path.exists(OUTPUT_DIR_JF):
             with open(OUTPUT_REPORT_JF, "w", encoding="utf-8") as f: f.write(html_public)
             print(f"Backup creato: {OUTPUT_REPORT_JF}")

        webbrowser.open(f"file://{os.path.abspath(OUTPUT_ADMIN)}")

    except Exception as e: print(f"Errore scrittura file: {e}")

if __name__ == "__main__":
    genera_app()