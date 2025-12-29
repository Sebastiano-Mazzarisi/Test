# Nome script: jf-report.py
# Data modifica: 29/12/2025 - FIX LOGICA ESCLUSIONI (SUBSTRING)
# Descrizione: Genera l'ecosistema report JOYFIT.
#
# Changelog:
# - RIPRISTINATA logica esclusioni "contiene" (es. Mario, Massimo).
# - Mantenuta logica Alias avanzata (=) con normalizzazione spazi/case.

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

# ================= CONFIGURAZIONE =================
PATHS = {
    "PDF_URL": r"C:\Dropbox\Prog\Monitor\JF-Calendari.pdf",
    "DATE_FILE": r"C:\Dropbox\Prog\Monitor\JF-DB.txt",
    "CSV_FILE": r"C:\Dropbox\Prog\Monitor\JF-DB.csv",
    "DUPLICATI_FILE": r"C:\Dropbox\Prog\Monitor\JF-Duplicati.txt",
    "OUT_DIR": r"C:\Dropbox\Prog\Monitor",
    "BACKUP_DIR": r"C:\Dropbox\Prog\JF"
}

FILES = {
    "REPORT": "JF-Report.html",
    "ADMIN": "JF-Report-ADMIN.html",
    "CONTA": "JF-Conta.html"
}

SETTINGS = {
    "START_DATE": datetime(2025, 9, 1),
    "END_DATE": datetime(2026, 8, 31),
    "ICON_URL": "https://raw.githubusercontent.com/Sebastiano-Mazzarisi/Test/main/JoyFit.jpg",
    "DEFAULT_REF_DATE": "20/12/2025"
}

CONSTS = {
    "MESI": ["SET", "OTT", "NOV", "DIC", "GEN", "FEB", "MAR", "APR", "MAG", "GIU", "LUG", "AGO"],
    "MESI_NUM": {"SET": 9, "OTT": 10, "NOV": 11, "DIC": 12, "GEN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAG": 5, "GIU": 6, "LUG": 7, "AGO": 8},
    "GIORNI": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"],
    "GIORNI_FULL": ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
}

# ================= UTILS PYTHON =================
def clean_money(val):
    if not val: return 0.0
    v = str(val).replace("€", "").replace(" ", "").strip().replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

def fmt_num(n):
    return f"{n:,.0f}".replace(",", ".")

def normalize_name_key(text):
    """
    Rimuove spazi extra, spazi doppi e converte in minuscolo per il confronto.
    Es: "  Biancoo   Francesco " -> "biancoo francesco"
    """
    if not text: return ""
    return " ".join(str(text).split()).lower()

def normalize_name_display(text):
    """
    Rimuove solo spazi extra e doppi, mantenendo il case originale.
    Es: "  Bianco   Francesco " -> "Bianco Francesco"
    """
    if not text: return ""
    return " ".join(str(text).split())

def load_ref_date(path):
    if not os.path.exists(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            matches = re.findall(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", f.read(500))
            return matches[-1] if matches else None
    except: return None

def open_pdf(source):
    try:
        if source.startswith("http"):
            print(f"Download PDF: {source}...")
            r = requests.get(source, timeout=10)
            r.raise_for_status()
            return pdfplumber.open(io.BytesIO(r.content))
        elif os.path.exists(source):
            print(f"Apertura PDF locale: {source}...")
            return pdfplumber.open(source)
    except Exception as e:
        print(f"Err PDF: {e}")
    return None

def load_duplicates_rules(path):
    """
    Carica le regole dal file TXT.
    - "=" -> ALIAS (Sostituzione esatta normalizzata).
    - "," -> ESCLUSIONE (Substring check).
    """
    exclusions = [] # Lista di tuple per iterazione (substring check)
    aliases = {}    # Dizionario per accesso diretto (sostituzione)
    
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    
                    # 1. ALIAS (es. Pippo Franco = F. Pippo)
                    if "=" in line:
                        parts = line.split("=")
                        if len(parts) >= 2:
                            # Nome Corretto: puliamo solo gli spazi
                            correct_name = normalize_name_display(parts[0])
                            # Nome Sbagliato: chiave normalizzata (minuscolo, no doppi spazi)
                            wrong_key = normalize_name_key(parts[1])
                            if correct_name and wrong_key:
                                aliases[wrong_key] = correct_name

                    # 2. ESCLUSIONI (es. Maria, Mario)
                    elif "," in line:
                        parts = line.split(",")
                        if len(parts) >= 2:
                            # Qui salviamo le stringhe minuscole per il controllo "in" (substring)
                            n1 = normalize_name_key(parts[0])
                            n2 = normalize_name_key(parts[1])
                            if n1 and n2:
                                exclusions.append((n1, n2))
        except: pass
    return exclusions, aliases

# ================= LOGICA DATI (ETL) =================
def process_csv_data():
    data_struct = {m: {} for m in CONSTS["MESI"]}
    transactions = []
    totals = {}
    
    # Caricamento regole
    exclusion_rules, alias_rules = load_duplicates_rules(PATHS["DUPLICATI_FILE"])
    
    if not os.path.exists(PATHS["CSV_FILE"]): return data_struct, transactions, {}

    encoding = 'utf-8-sig'
    try:
        with open(PATHS["CSV_FILE"], "r", encoding=encoding) as f: f.read(1024)
    except: encoding = 'latin1'

    try:
        with open(PATHS["CSV_FILE"], "r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f, delimiter=';' if ';' in f.read(1024) else ',')
            f.seek(0)
            header_skipped = False
            
            for row in reader:
                if not row: continue
                s_row = "".join(row).lower()
                if not header_skipped and "data" in s_row and "nominativo" in s_row:
                    header_skipped = True; continue
                if len(row) <= 6: continue
                
                raw_input_nom = row[2] 
                
                # --- APPLICAZIONE ALIAS (Correzione) ---
                search_key = normalize_name_key(raw_input_nom)
                if search_key in alias_rules:
                    current_nom = alias_rules[search_key]
                else:
                    current_nom = normalize_name_display(raw_input_nom)
                
                if current_nom and current_nom[0].isalpha():
                    nom = current_nom.title()
                else:
                    nom = "[Altro]"
                # ---------------------------------------
                
                dt = None
                for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                    try: dt = datetime.strptime(row[1].strip(), fmt); break
                    except: pass
                
                if dt and SETTINGS["START_DATE"] <= dt <= SETTINGS["END_DATE"]:
                    val = clean_money(row[5]) + clean_money(row[6])
                    if val <= 0: continue
                    
                    totals[nom] = totals.get(nom, 0.0) + val
                    transactions.append({
                        "date_str": dt.strftime("%d/%m/%Y"),
                        "ts": dt.timestamp(),
                        "nome": nom,
                        "att": row[3].strip() if len(row)>3 else "",
                        "imp": val
                    })
                    
                    m_str = next((k for k,v in CONSTS["MESI_NUM"].items() if v == dt.month), None)
                    if m_str and m_str in data_struct:
                        if dt.day not in data_struct[m_str]: data_struct[m_str][dt.day] = []
                        data_struct[m_str][dt.day].append({"nome": nom, "imp": val})

    except Exception as e: print(f"Err CSV: {e}")

    # --- LOGICA RILEVAMENTO DUPLICATI (Ripristinata logica "Contiene") ---
    dupes = {}
    names = sorted([n for n, v in totals.items() if v > 0 and n != "[Altro]"])
    grouped = {}
    
    for n in names: grouped.setdefault(n[0].upper(), []).append(n)
    
    for grp in grouped.values():
        if len(grp) < 2: continue
        for n in grp:
            matches = difflib.get_close_matches(n, grp, n=5, cutoff=0.85)
            matches = [m for m in matches if m != n]
            filtered = []
            
            if matches:
                n_lower = n.lower() # Per confronto "in"
                
                for cand in matches:
                    cand_lower = cand.lower()
                    is_excluded = False
                    
                    # LOGICA SUBSTRING: Se le regole (es. mario, massimo) sono CONTENUTE nei nomi, escludi.
                    for r1, r2 in exclusion_rules:
                        # Controllo incrociato: r1 in nome A E r2 in nome B (o viceversa)
                        if (r1 in n_lower and r2 in cand_lower) or (r2 in n_lower and r1 in cand_lower):
                            is_excluded = True
                            break
                    
                    if not is_excluded:
                        filtered.append(cand)
                        
            if filtered: dupes[n] = filtered
            
    return data_struct, transactions, dupes

def process_pdf_data():
    monthly = {"2024-25": {m: 0.0 for m in CONSTS["MESI"]}, "2025-26": {m: 0.0 for m in CONSTS["MESI"]}}
    daily = {m: [] for m in CONSTS["MESI"]}
    
    pdf = open_pdf(PATHS["PDF_URL"])
    if not pdf: return monthly, daily

    try:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            year = "2025-26" if "2025-26" in txt else ("2024-25" if "2024-25" in txt else None)
            if not year: continue
            
            tables = page.extract_table()
            if not tables: continue
            
            header_idx = -1
            for i, row in enumerate(tables):
                clean_row = [str(x).strip().upper()[:3] for x in row if x]
                if sum(1 for x in clean_row if x in CONSTS["MESI"]) > 5:
                    header_idx = i; break
            
            if header_idx != -1:
                headers = tables[header_idx]
                for row in tables[header_idx+1:]:
                    for c_idx, cell in enumerate(row):
                        if c_idx < len(headers) and cell:
                            m_head = str(headers[c_idx]).strip().upper()[:3].replace('"','')
                            if m_head in CONSTS["MESI"]:
                                vals = [clean_money(x) for x in re.findall(r"(?<!\d)(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", str(cell))]
                                if vals:
                                    monthly[year][m_head] = max(monthly[year][m_head], max(vals))
                                    if year == "2025-26":
                                        day_match = re.search(r"\b(\d{1,2})\s+(Lu|Ma|Me|Gi|Ve|Sa|Do)\b", str(cell), re.IGNORECASE)
                                        if day_match:
                                            d_val = vals[-1] if vals and vals[-1] < 10000 else 0
                                            if d_val > 0:
                                                d_num = int(day_match.group(1))
                                                found = False
                                                for existing in daily[m_head]:
                                                    if existing["num"] == d_num:
                                                        existing["valore"] = max(existing["valore"], d_val)
                                                        found = True; break
                                                if not found: daily[m_head].append({"num": d_num, "valore": d_val})

    except Exception as e: print(f"Err PDF: {e}")
    finally: pdf.close()
    
    for m in CONSTS["MESI"]: daily[m].sort(key=lambda x: x["num"])
    return monthly, daily

def prepare_json_data(monthly, daily, trans_struct, all_trans, dupes, ref_date_str):
    try: ref_dt = datetime.strptime(ref_date_str, "%d/%m/%Y")
    except: ref_dt = datetime.now()
    
    j_data = {}
    tot_24 = sum(monthly["2024-25"].values())
    tot_cons = 0.0
    tot_proj = 0.0
    
    global_idx = []
    global_aggr = {}
    
    for m in CONSTS["MESI"]:
        m_num = CONSTS["MESI_NUM"][m]
        year = 2025 if m_num >= 9 else 2026
        v_24 = monthly["2024-25"][m]
        v_25_tot = monthly["2025-26"][m]
        
        days_in_m = calendar.monthrange(year, m_num)[1]
        day_map = {x["num"]: x["valore"] for x in daily[m]}
        
        d_list = []
        d_details = {}
        t_cons_m = 0.0
        t_prev_m = 0.0
        
        breakeven = None
        run_sum = 0.0
        
        for d in range(1, days_in_m + 1):
            curr_dt = datetime(year, m_num, d)
            is_past = curr_dt <= ref_dt
            val = day_map.get(d, 0.0)
            
            # Transactions
            raw_t = trans_struct[m].get(d, [])
            if is_past:
                t_cons_m += val
                run_sum += val
                if not breakeven and v_24 > 0 and run_sum >= v_24: breakeven = f"{d}/{m_num}"
                
                if raw_t:
                    t_aggr = {}
                    for t in raw_t:
                        nm, imp = t["nome"], t["imp"]
                        t_aggr[nm] = t_aggr.get(nm, 0.0) + imp
                        
                        # Global Aggregator
                        if nm not in global_aggr: global_aggr[nm] = {"tot": 0.0, "last": curr_dt}
                        global_aggr[nm]["tot"] += imp
                        if curr_dt > global_aggr[nm]["last"]: global_aggr[nm]["last"] = curr_dt
                    
                    final_t = [{"nome": k, "imp": v} for k,v in t_aggr.items()]
                    final_t.sort(key=lambda x: x["nome"].lower())
                    
                    d_details[str(d)] = {
                        "date_full": f"{d}/{m_num}/{str(year)[-2:]}",
                        "title_day_name": CONSTS["GIORNI_FULL"][curr_dt.weekday()],
                        "title_date": f"{d}/{m_num}/{year}",
                        "trans": final_t,
                        "tot_day": sum(x["imp"] for x in final_t)
                    }
                    global_idx.append({"m": m, "d": d, "ts": curr_dt.timestamp()})
                    
                d_list.append({"giorno": f"{d:02d} {CONSTS['GIORNI'][curr_dt.weekday()]}", "cons": val, "prev": 0.0, "day_num": d})
            else:
                t_prev_m += val
                d_list.append({"giorno": f"{d:02d} {CONSTS['GIORNI'][curr_dt.weekday()]}", "cons": 0.0, "prev": val, "day_num": d})

        # Adjust totals logic
        sum_days = t_cons_m + t_prev_m
        if sum_days == 0 and v_25_tot > 0:
            start_m = datetime(year, m_num, 1)
            if start_m > ref_dt: t_prev_m = v_25_tot
            elif start_m.month == ref_dt.month: t_prev_m = v_25_tot 
            else: t_cons_m = v_25_tot
        elif v_25_tot > sum_days:
            diff = v_25_tot - sum_days
            if datetime(year, m_num, 1) > ref_dt: t_prev_m += diff
            else: t_cons_m += diff

        full_m = t_cons_m + t_prev_m
        tot_cons += t_cons_m
        tot_proj += full_m
        
        # UI Text Logic
        prev_txt, prev_style = "", ""
        if t_prev_m > 0:
            prev_txt = fmt_num(t_prev_m)
            prev_style = "bg-yellow"
        elif t_cons_m > 0 and v_24 > 0:
            diff_pct = ((t_cons_m - v_24) / v_24) * 100
            prev_txt = f"{diff_pct:+.1f}%".replace('.', ',')
            prev_style = "text-pct-small"

        j_data[m] = {
            "nome_esteso": f"{m} {year}", "title_mese": CONSTS["MESI"][CONSTS["MESI"].index(m)], "title_anno": str(year),
            "tot_24_25": v_24, "tot_cons": t_cons_m, "tot_prev": t_prev_m, "tot_full": full_m,
            "lista_giorni": d_list, "dettagli": d_details, "breakeven": breakeven,
            "home_data": {"old": fmt_num(v_24) if v_24>0 else "", "cons": fmt_num(t_cons_m) if t_cons_m>0 else "", "prev_txt": prev_txt, "prev_style": prev_style}
        }

    # Final Lists
    global_idx.sort(key=lambda x: x["ts"])
    g_list = [{"nome": k, "imp": v["tot"], "last_date": v["last"].strftime("%d/%m/%Y"), "ts": v["last"].timestamp()} for k,v in global_aggr.items()]
    g_list.sort(key=lambda x: x["nome"].lower())

    # Timeline for Graph
    timeline = []
    for m in CONSTS["MESI"]:
        m_n = CONSTS["MESI_NUM"][m]
        y = 2025 if m_n >= 9 else 2026
        dm = {x["num"]: x["valore"] for x in daily[m]}
        for d in range(1, calendar.monthrange(y, m_n)[1]+1):
            timeline.append({"ts": datetime(y,m_n,d).timestamp(), "date": f"{d}/{m_n}", "val": dm.get(d, 0.0)})

    j_data.update({
        "GLOBAL_DAY_INDEX": global_idx, "GLOBAL_LIST": g_list,
        "ALL_TRANSACTIONS": sorted(all_trans, key=lambda x: x['ts']),
        "DUPLICATES_MAP": dupes, "FORECAST_TIMELINE": timeline,
        "GLOBAL_STATS": {"tot_annuo": tot_cons, "tot_ref": tot_24, "tot_cons": tot_cons, "tot_prev": tot_proj, "data_rif": ref_date_str}
    })
    return j_data, tot_24, tot_cons, tot_proj

# ================= FRONTEND (CSS/JS) =================
CSS_STYLES = """
<style>
    :root { --blue: #1a3b5c; --bg: #cfd8dc; --white: #ffffff; }
    body { background-color: var(--bg); font-family: -apple-system, sans-serif; font-size: 26px; padding: 10px 0; color: #111827; overscroll-behavior-y: none; }
    #loading-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; display:none; flex-direction:column; justify-content:center; align-items:center; color:white; font-size:2rem; font-weight:bold; text-align:center; }
    #copy-toast { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: #e5e7eb; color: black; padding: 15px 25px; border-radius: 8px; font-weight: bold; font-size: 1.2rem; box-shadow: 0 4px 10px rgba(0,0,0,0.2); z-index: 20000; display: none; }
    .popup-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:10000; display:none; justify-content:center; align-items:center; }
    .popup-content { background:white; border-radius:12px; padding:25px; width:90%; max-width:400px; box-shadow:0 10px 25px rgba(0,0,0,0.3); position:relative; }
    .popup-header { background-color:var(--blue); color:white; padding:15px; text-align:center; font-weight:800; font-size:1.4rem; text-transform:uppercase; margin:-25px -25px 20px -25px; border-radius:12px 12px 0 0; }
    .popup-close-btn { position:absolute; top:12px; right:15px; font-size:1.8rem; cursor:pointer; color:white; font-weight:bold; line-height:1; }
    .popup-row { margin-bottom:15px; border-bottom:1px solid #eee; padding-bottom:10px; display:flex; justify-content:space-between; align-items:baseline; }
    .popup-label { font-size:1rem; color:#666; font-weight:bold; text-transform:uppercase; }
    .popup-val { font-size:1.6rem; font-weight:800; color:#111; }
    .popup-diff { font-size:1rem; font-weight:normal; margin-left:10px; }
    .popup-missing { font-size:1.1rem; color:#dc2626; margin-top:5px; font-weight:600; text-align:right; width:100%; display:block; }
    .main-wrapper { width:94%; max-width:600px; margin:0 auto; }
    .card-box { background:white; border-radius:16px; box-shadow:0 4px 15px rgba(0,0,0,0.15); overflow:hidden; margin-bottom:20px; border:1px solid black; }
    .header-blue { background-color:var(--blue); color:white; padding:10px; display:flex; justify-content:space-between; align-items:center; height:90px; }
    .header-title { font-size:1.6rem; font-weight:800; margin:0; text-transform:uppercase; text-align:center; cursor:pointer; line-height:1.1; }
    .btn-styled { background-color:#f1f5f9; color:var(--blue) !important; border-radius:8px; padding:5px 12px; font-size:1.8rem; cursor:pointer; box-shadow:0 2px 4px rgba(0,0,0,0.2); display:inline-block; }
    .nav-arrow { font-size:2.5rem; cursor:pointer; font-weight:bold; padding:0 15px; user-select:none; }
    .total-box { padding:30px 20px; text-align:center; border-bottom:1px solid #eee; }
    .total-amount { font-size:4.8rem; font-weight:900; color:#d97706; margin:0; transition:opacity 1s; }
    .chart-section { padding:25px 20px; }
    .bar-row { display:flex; align-items:center; margin-bottom:5px; font-size:1.2rem; cursor:pointer; }
    .bar-label-container { width:145px; flex-shrink:0; text-align:center; margin-right:5px; }
    .bar-label-text { font-weight:700; color:#000; font-size:1.3rem; border:4px solid transparent; padding:2px 5px; border-radius:4px; }
    .bar-value { width:140px; text-align:right; font-weight:800; color:#000; flex-shrink:0; }
    .progress { flex-grow:1; height:26px; margin:0 15px; border-radius:8px; width:40%; background:#e9ecef; }
    .progress-bar { height:100%; border-radius:8px; }
    .table-custom { width:100%; border-collapse:collapse; }
    .table-custom th, .table-custom td { border:1px solid black !important; padding:8px; text-align:center; font-size:1.6rem; line-height:1.1; }
    .table-custom th { background:#e5e7eb; color:#000 !important; font-size:1.1rem; font-weight:normal; }
    .bg-blue-light { background-color:#e3f2fd; } .bg-red-light { background-color:#fff1f2; color:#b91c1c; } .bg-yellow { background-color:#fef9c3; }
    .text-pct-small { font-size:1rem !important; } .text-gray { color:#9ca3af; }
    .footer-note { font-size:1rem; text-align:center; padding:20px; background:#f3f4f6; }
    .prediction-note { font-size:1rem; padding:15px; text-align:center; border-top:1px solid black; border-bottom:1px solid black; line-height:1.3; }
    .row-total td, tfoot td { background-color:#d1d5db; font-weight:900 !important; border-bottom:1px solid black !important; }
    .search-container { padding:15px; display:flex; justify-content:center; background:#f8fafc; border-bottom:1px solid #e2e8f0; }
    .search-input { width:100%; max-width:400px; padding:10px 15px; border-radius:8px; border:1px solid #cbd5e1; font-size:1.1rem; }
    .name-link { cursor:pointer; color:var(--blue); text-decoration:underline; }
    .dupe-box { margin:15px 20px; padding:15px; background:#fff7ed; border:1px solid #ffedd5; border-radius:8px; display:none; }
    .dupe-item { display:inline-block; background:white; padding:5px 10px; margin:3px; border-radius:15px; border:1px solid #fdba74; color:#9a3412; font-size:0.95rem; cursor:pointer; }
    .clickable-row { cursor:pointer; } .clickable-row:active { background-color:#dbeafe; }
    .col-idx { width:40px; font-size:0.9rem !important; color:#666; } .col-small { font-size:0.9rem !important; width:50px; }
    .col-nom { text-align:left !important; padding-left:10px !important; font-size:1.3rem !important; }
    .col-imp { text-align:right !important; padding-right:10px !important; color:#b91c1c !important; }
    .col-data { font-size:0.9rem !important; color:#555; width:110px; }
    .col-att { text-align:left !important; font-size:1.1rem !important; color:#555; }
    #view-global .col-nom, #view-global .col-imp, #view-global .col-data,
    #view-customer .col-att, #view-customer .col-imp, #view-customer .col-data, #view-day .col-nom, #view-day .col-imp { text-align:center !important; padding:0 5px !important; }
    .sort-icon { color:red; margin-right:5px; font-size:0.8em; display:none; }
    @media (max-width:480px) {
        .table-custom td { padding:8px 2px !important; font-size:1.4rem; }
        .total-amount { font-size:3.8rem; }
        .bar-label-container { width:85px; margin-right:2px; } .bar-label-text { font-size:0.8rem; } .bar-value { width:95px; font-size:0.85rem; }
        .header-title { font-size:1.3rem; }
        .col-idx { width:25px; font-size:0.7rem !important; } .col-nom { font-size:1.1rem !important; } .col-imp { font-size:0.9rem !important; }
        .col-data { width:75px; font-size:0.8rem !important; } .col-att { font-size:0.85rem !important; line-height:1.2; }
        .main-wrapper { width:98%; padding:5px; }
    }
</style>
"""

JS_SCRIPT = """
<script>
    // --- STATE & UTILS ---
    const dati = DATA_PLACEHOLDER;
    const mesiOrdine = MESI_PLACEHOLDER;
    const isAdmin = IS_ADMIN_PLACEHOLDER;
    const globalIndex = dati.GLOBAL_DAY_INDEX; 
    const BASE_API = "https://countapi.mileshilliard.com/api/v1";
    const NAMESPACE = "joyfit-stats-v1";
    
    let state = {
        view: 'view-home', month: null, dayNum: 0, custName: '', custTrans: [],
        scrollPos: 0, lastView: 'view-home',
        sort: { 
            day: { col: 'nom', dir: 'asc' },
            month: { col: 'day', dir: 'asc' },
            global: { col: 'nom', dir: 'asc', search: '' },
            cust: { col: 'data', dir: 'desc' } // DEFAULT DESC
        }
    };

    const fmt = n => n > 0 ? Math.round(n).toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".") : "";
    const fmtFull = n => n >= 0 ? Math.round(n).toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".") : "0";
    const el = id => document.getElementById(id);
    const track = page => { if(!isAdmin) fetch(`${BASE_API}/hit/${NAMESPACE}_${page}`, {mode:'cors'}).catch(()=>{}); };

    // --- NAVIGATION ---
    function switchView(id) {
        document.querySelectorAll('.main-wrapper > div').forEach(d => d.style.display = 'none');
        el(id).style.display = 'block';
        if(state.view !== id) state.lastView = state.view;
        state.view = id;
        window.scrollTo(0,0);
        resetIdle();
    }

    function changeView(dir) {
        const views = ['view-home', ...mesiOrdine.map(m=>'view-detail-'+m)]; // Virtual IDs
        let currIdx = state.view === 'view-home' ? 12 : mesiOrdine.indexOf(state.month);
        let nextIdx = (currIdx + dir + 13) % 13;
        if(nextIdx === 12) showHome(); else showDetail(mesiOrdine[nextIdx]);
    }

    function showHome() {
        state.month = null;
        initHomeTable();
        switchView('view-home');
        track('report_home');
    }

    function showDetail(mese) {
        state.month = mese;
        const d = dati[mese];
        el('detail-title').innerHTML = d.title_mese + "<br>" + d.title_anno;
        el('detail-total-display').innerText = fmtFull(d.tot_full) + ' €';
        
        // Chart
        const maxV = Math.max(d.tot_24_25, d.tot_full) || 1;
        el('detail-chart').innerHTML = `
            <div class="bar-row" onclick="showStatsPopup('${mese}')"><div class="bar-label-container"><span class="bar-label-text" id="label-d-0">2024-25</span></div><div class="progress"><div class="progress-bar bg-primary" style="width:${(d.tot_24_25/maxV)*100}%"></div></div><span class="bar-value">${fmtFull(d.tot_24_25)} €</span></div>
            <div class="bar-row" onclick="showStatsPopup('${mese}')"><div class="bar-label-container"><span class="bar-label-text" id="label-d-1">2025-26</span></div><div class="progress"><div class="progress-bar bg-danger" style="width:${(d.tot_cons/maxV)*100}%"></div></div><span class="bar-value">${fmtFull(d.tot_cons)} €</span></div>
            <div class="bar-row" onclick="showStatsPopup('${mese}')"><div class="bar-label-container"><span class="bar-label-text" id="label-d-2">Previsto</span></div><div class="progress"><div class="progress-bar bg-warning" style="width:${(d.tot_full/maxV)*100}%"></div></div><span class="bar-value">${fmtFull(d.tot_full)} €</span></div>
        `;
        
        renderMonthTable(mese);
        switchView('view-detail');
        track('report_' + mese);
    }

    function showDay(mese, dayNum) {
        const details = dati[mese].dettagli[dayNum];
        if(!details) return;
        state.month = mese; state.dayNum = parseInt(dayNum);
        el('day-title').innerHTML = details.title_day_name + "<br>" + details.title_date;
        el('stats-day').innerText = fmtFull(details.tot_day);
        el('stats-month').innerText = fmtFull(dati[mese].tot_cons);
        el('stats-year').innerText = fmtFull(dati["GLOBAL_STATS"].tot_annuo);
        renderDayTable(details.trans);
        switchView('view-day');
        track('report_' + mese + '_day');
    }

    function showGlobalList() {
        state.sort.global = {col: 'nom', dir: 'asc', search: ''};
        el('global-search').value = "";
        renderGlobalTable();
        switchView('view-global');
        track('report_global_list');
    }

    function showCustomer(name) {
        if(state.view === 'view-global') state.scrollPos = window.scrollY;
        state.custName = name;
        el('cust-title').innerText = name;
        
        // Reset sort to default if entering view
        if(state.view !== 'view-customer') state.sort.cust = { col: 'data', dir: 'desc' };

        // Duplicates
        const dupes = dati.DUPLICATES_MAP[name];
        const box = el('cust-duplicates');
        box.style.display = (dupes && dupes.length) ? 'block' : 'none';
        if(dupes) el('dupe-list').innerHTML = dupes.map(d => `<span class="dupe-item" onclick="showCustomer('${d}')">${d}</span>`).join('');

        renderCustomerTable();
        switchView('view-customer');
        track('report_cust_detail');
    }

    function closeCustomer() {
        el('view-customer').style.display = 'none';
        if(state.lastView === 'view-global') {
            el('view-global').style.display = 'block';
            state.view = 'view-global';
            setTimeout(()=>window.scrollTo(0, state.scrollPos), 10);
        } else showHome();
    }

    // --- SORTING & RENDERING GENERICS ---
    function applySort(list, mode) {
        const s = state.sort[mode];
        return list.sort((a,b) => {
            let valA, valB;
            if(mode === 'month') { valA = s.col==='day'?a.day_num : a[s.col]; valB = s.col==='day'?b.day_num : b[s.col]; }
            else if(mode === 'day' || mode === 'global') {
                if(s.col === 'nom') { valA = a.nome.toLowerCase(); valB = b.nome.toLowerCase(); }
                else if(s.col === 'imp') { valA = a.imp; valB = b.imp; }
                else if(s.col === 'data') { valA = a.ts; valB = b.ts; }
            }
            else if(mode === 'cust') {
                if(s.col === 'data') { valA = a.ts; valB = b.ts; }
                else if(s.col === 'imp') { valA = a.imp; valB = b.imp; }
                else if(s.col === 'att') { valA = (a.att||"").toLowerCase(); valB = (b.att||"").toLowerCase(); }
            }
            if (valA < valB) return s.dir === 'asc' ? -1 : 1;
            if (valA > valB) return s.dir === 'asc' ? 1 : -1;
            return 0;
        });
    }

    function handleSortClick(mode, col) {
        const s = state.sort[mode];
        if (s.col === col) s.dir = s.dir === 'asc' ? 'desc' : 'asc';
        else {
            s.col = col;
            // Default directions logic
            if (mode === 'cust' && (col === 'data' || col === 'imp')) s.dir = 'desc';
            else if (mode === 'global' && col === 'data') s.dir = 'desc';
            else s.dir = 'asc';
        }
        
        // Re-render
        if(mode === 'month') renderMonthTable(state.month);
        else if(mode === 'day') renderDayTable(dati[state.month].dettagli[state.dayNum].trans);
        else if(mode === 'global') renderGlobalTable();
        else if(mode === 'cust') renderCustomerTable();
    }

    function updateSortIcons(mode) {
        ['nom','imp','data','day','cons','prev','att'].forEach(k => { const i=el((mode==='global'?'g-':(mode==='cust'?'c-':(mode==='month'?'m-':'')))+'icon-'+k); if(i) i.style.display='none'; });
        const active = el((mode==='global'?'g-':(mode==='cust'?'c-':(mode==='month'?'m-':'')))+'icon-'+state.sort[mode].col);
        if(active) { active.style.display = 'inline'; active.innerHTML = state.sort[mode].dir === 'asc' ? '&#9660;' : '&#9650;'; }
    }

    // --- RENDERERS ---
    function initHomeTable() {
        const tbody = el('table-body-home'); tbody.innerHTML = '';
        mesiOrdine.forEach((m, i) => {
            const d = dati[m];
            const tr = document.createElement('tr'); tr.className = 'clickable-row'; tr.onclick = () => { showDetail(m); };
            tr.innerHTML = `<td>${m}</td><td class="bg-blue-light">${d.home_data.old}</td><td class="${d.home_data.cons?'bg-red-light':'text-gray'}">${d.home_data.cons}</td><td class="${d.home_data.prev_style}">${d.home_data.prev_txt}</td><td class="col-small">${d.breakeven||""}</td>`;
            tbody.appendChild(tr);
        });
    }

    function renderMonthTable(mese) {
        updateSortIcons('month');
        const list = applySort([...dati[mese].lista_giorni], 'month');
        const tbody = el('detail-table-body'); tbody.innerHTML = '';
        list.forEach(d => {
            const tr = document.createElement('tr');
            if(d.cons==0 && d.prev==0) tr.className = 'row-empty';
            let cons = `<td class="col-val text-gray">${fmt(d.cons)}</td>`;
            if(d.cons>0) cons = `<td class="col-val bg-red-light clickable-cell" onclick="showDay('${mese}','${d.day_num}')">${fmt(d.cons)}</td>`;
            tr.innerHTML = `<td class="col-giorno">${d.giorno}</td>${cons}<td class="col-val ${d.prev?'bg-yellow':''}">${fmt(d.prev)}</td>`;
            tbody.appendChild(tr);
        });
        const trT = document.createElement('tr'); trT.className='row-total clickable-row'; trT.onclick=()=>showStatsPopup(mese);
        trT.innerHTML = `<td>TOT</td><td>${fmtFull(dati[mese].tot_cons)}</td><td>${fmtFull(dati[mese].tot_prev)}</td>`;
        tbody.appendChild(trT);
    }

    function renderDayTable(transList) {
        updateSortIcons('day');
        const list = applySort([...transList], 'day');
        const tbody = el('day-table-body'); tbody.innerHTML = '';
        list.forEach((t, i) => {
            const isDupe = dati.DUPLICATES_MAP[t.nome] && dati.DUPLICATES_MAP[t.nome].length > 0;
            const tr = document.createElement('tr');
            tr.innerHTML = `<td class="col-idx">${i+1}</td><td class="col-nom name-link" style="${isDupe?'color:#0044cc;font-weight:bold':''}" onclick="showCustomer('${t.nome}')">${t.nome}</td><td class="col-imp">${fmt(t.imp)}</td>`;
            tbody.appendChild(tr);
        });
    }

    function renderGlobalTable() {
        updateSortIcons('global');
        let list = [...dati.GLOBAL_LIST];
        const term = state.sort.global.search.toLowerCase();
        if(term) list = list.filter(x => x.nome.toLowerCase().includes(term));
        el('btn-clear-search').style.display = term ? 'block' : 'none';
        el('global-filter-count').innerText = `(${list.length})`;
        el('global-total-foot').innerText = fmtFull(list.reduce((a,b)=>a+b.imp,0));
        
        list = applySort(list, 'global');
        const tbody = el('global-table-body'); tbody.innerHTML = '';
        let lastM = "";
        list.forEach((t, i) => {
            const currM = t.last_date.substring(3);
            const tr = document.createElement('tr');
            if(i>0 && currM!==lastM) tr.className = "row-month-change";
            lastM = currM;
            const isDupe = dati.DUPLICATES_MAP[t.nome];
            tr.innerHTML = `<td class="col-idx">${i+1}</td><td class="col-data">${t.last_date}</td><td class="col-nom name-link" style="${isDupe?'color:#0044cc;font-weight:bold':''}" onclick="showCustomer('${t.nome}')">${t.nome}</td><td class="col-imp">${fmt(t.imp)}</td>`;
            tbody.appendChild(tr);
        });
    }

    function renderCustomerTable() {
        updateSortIcons('cust');
        let trans = dati.ALL_TRANSACTIONS.filter(t => t.nome === state.custName);
        trans = applySort(trans, 'cust');
        state.custTrans = trans; // Save for copy
        
        const tbody = el('cust-table-body'); tbody.innerHTML = '';
        let tot = 0;
        trans.forEach((t, i) => {
            tot += t.imp;
            const tr = document.createElement('tr');
            tr.innerHTML = `<td class="col-idx">${i+1}</td><td class="col-data">${t.date_str}</td><td class="col-att">${t.att}</td><td class="col-imp">${fmt(t.imp)}</td>`;
            tbody.appendChild(tr);
        });
        el('cust-total-foot').innerText = fmtFull(tot);
    }

    // --- ACTIONS ---
    function copyCustomerData() {
        if (!state.custTrans.length) return;
        const tot = state.custTrans.reduce((a, b) => a + b.imp, 0);
        let txt = `${state.custName.toUpperCase()} (${fmt(tot)} €)\\n-----\\n`;
        state.custTrans.forEach(t => {
            txt += `${t.date_str} ${t.att || "..."} (${fmt(t.imp)} €)\\n`;
        });
        txt += "-----\\n\\n"; // EXTRA NEWLINE
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(txt).then(() => {
                el('copy-toast').style.display = 'block';
                setTimeout(() => el('copy-toast').style.display = 'none', 1000);
            }).catch(alert);
        } else alert("Copia non supportata");
    }

    function showStatsPopup(k) {
        let ref, cons, prev, title, sub;
        if (!k) {
            const s = dati.GLOBAL_STATS; ref = s.tot_ref; cons = s.tot_cons; prev = s.tot_prev;
            title = "RIEPILOGO STAGIONE"; sub = "STAGIONE 2024-25";
        } else {
            const d = dati[k]; ref = d.tot_24_25; cons = d.tot_cons; prev = d.tot_full;
            title = d.title_mese + " " + d.title_anno; sub = d.title_mese + " " + (parseInt(d.title_anno)-1);
        }
        const diffCons = cons - ref; const pctCons = (diffCons/(ref||1))*100;
        const diffPrev = prev - ref; const pctPrev = (diffPrev/(ref||1))*100;
        
        let html = `
            <div class="popup-header">${title}</div>
            <div class="popup-row"><div class="popup-label">${sub}</div><div class="popup-val" style="color:#0d6efd">${fmtFull(ref)} €</div></div>
            <div class="popup-row"><div class="popup-label">CONSUNTIVO</div><div class="popup-val" style="color:#b91c1c">${fmtFull(cons)} € <span class="popup-diff" style="color:#b91c1c">(${pctCons>=0?'+':''}${pctCons.toFixed(1).replace('.',',')}%)</span></div>
            ${(ref-cons)>0 ? `<div class="popup-missing">Mancano ${fmtFull(ref-cons)} €</div>` : ''}</div>
            <div class="popup-row"><div class="popup-label">PREVISTO</div><div class="popup-val" style="color:#d97706">${fmtFull(prev)} € <span class="popup-diff" style="color:#d97706">(${pctPrev>=0?'+':''}${pctPrev.toFixed(1).replace('.',',')}%)</span></div>
            ${(prev-cons)>0 ? `<div class="popup-missing">Mancano ${fmtFull(prev-cons)} €</div>` : ''}</div>
        `;
        el('popup-inner').innerHTML = html;
        el('info-popup').style.display = 'flex';
    }

    // --- PRINTING & UTILS ---
    async function printCurrentView() {
        el('loading-overlay').style.display = 'flex';
        setTimeout(async () => {
            try {
                const target = document.querySelector('.main-wrapper > div[style*="block"]');
                if(!target) return;
                const canvas = await html2canvas(target, {scale:2, useCORS:true});
                const doc = new window.jspdf.jsPDF('p','mm','a4');
                const img = canvas.toDataURL('image/jpeg', 0.65);
                const props = doc.getImageProperties(img);
                const pdfH = (props.height * 180) / props.width;
                doc.addImage(img, 'JPEG', 15, 15, 180, Math.min(pdfH, 267));
                doc.save(`Report_${new Date().getTime()}.pdf`);
            } catch(e) { alert(e); }
            el('loading-overlay').style.display = 'none';
        }, 100);
    }
    
    function filterGlobal(v) { state.sort.global.search = v; renderGlobalTable(); }
    function clearSearch() { state.sort.global.search = ""; el('global-search').value = ""; renderGlobalTable(); }
    function closePopup() { el('info-popup').style.display = 'none'; }
    function navDay(d) {
        const idx = globalIndex.findIndex(x => x.m===state.month && x.d===state.dayNum);
        if(idx!==-1 && globalIndex[idx+d]) showDay(globalIndex[idx+d].m, globalIndex[idx+d].d);
    }
    function closeDayDetail() { showDetail(state.month); setTimeout(()=>el('row-day-'+state.dayNum)?.scrollIntoView({block:'center'}),50); }

    // --- IDLE ROTATION ---
    let valIdx = 0, idleT, rotI;
    const vals = ["tot_full", "tot_24_25", "tot_cons"];
    const colors = ['#d97706', '#0d6efd', '#dc3545'];
    
    function cycleValues() {
        if(state.view!=='view-home' && state.view!=='view-detail') return;
        valIdx = (valIdx + 1) % 3;
        const prefix = state.view==='view-home' ? 'h' : 'd';
        [0,1,2].forEach(i => el(`label-${prefix}-${i}`).style.borderColor = 'transparent');
        // Map visual order (2, 0, 1) to data index
        const mapId = [2, 0, 1]; 
        el(`label-${prefix}-${mapId[valIdx]}`).style.border = `4px solid ${colors[valIdx]}`;
        
        const disp = el(state.view==='view-home' ? 'home-total-display' : 'detail-total-display');
        disp.style.opacity = 0;
        setTimeout(() => {
            let val = 0;
            if(state.view==='view-home') val = dati.GLOBAL_STATS[["tot_prev", "tot_ref", "tot_cons"][valIdx]]; // Note mapping
            else val = dati[state.month][["tot_full", "tot_24_25", "tot_cons"][valIdx]];
            disp.innerText = fmtFull(val) + " €";
            disp.style.color = colors[valIdx];
            disp.style.opacity = 1;
        }, 500);
    }

    function resetIdle() {
        clearInterval(rotI); clearTimeout(idleT);
        valIdx = 0;
        // Reset Visuals
        ['h','d'].forEach(p => [0,1,2].forEach(i => {
             const lbl = el(`label-${p}-${i}`); if(lbl) lbl.style.borderColor = 'transparent';
        }));
        if(state.view==='view-home' || state.view==='view-detail') {
             const prefix = state.view==='view-home' ? 'h' : 'd';
             el(`label-${prefix}-0`).style.border = `4px solid ${colors[0]}`; // Old Year
             // Reset Text... simplified for brevity, assume user interaction resets to default view
        }
        idleT = setTimeout(() => { cycleValues(); rotI = setInterval(cycleValues, 10000); }, 10000);
    }

    ['mousemove','click','touchstart','scroll'].forEach(e => document.addEventListener(e, resetIdle));
    showHome();
</script>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Report JoyFit</title>
    <link rel="icon" href="{ICON}">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    {CSS}
</head>
<body>
<div id="loading-overlay"><div>Generazione PDF...</div></div>
<div id="copy-toast">Copiato!</div>

<div id="info-popup" class="popup-overlay" onclick="if(event.target===this) closePopup()"><div class="popup-content"><div class="popup-close-btn" onclick="closePopup()">&#10005;</div><div id="popup-inner"></div></div></div>

<div class="main-wrapper">
    <div id="view-home">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:80px; text-align:center;"><span onclick="showGlobalList()" class="btn-user btn-styled">&#129489;</span></div>
                <div style="flex-grow:1; display:flex; justify-content:space-between; align-items:center;">
                    <div class="nav-arrow" onclick="changeView(-1)">&#10094;</div>
                    <h1 class="header-title" onclick="printCurrentView()">INCASSI<br>2025-26</h1>
                    <div class="nav-arrow" onclick="changeView(1)">&#10095;</div>
                </div>
                <div style="width:80px; text-align:center"><span onclick="printCurrentView()" class="btn-styled">🖨️</span></div>
            </div>
            <div class="total-box"><div class="total-amount" id="home-total-display">{TOT_HOME} €</div></div>
            <div class="chart-section">
                <div class="bar-row" onclick="showStatsPopup()"><div class="bar-label-container"><span class="bar-label-text" id="label-h-0">2024-25</span></div><div class="progress"><div class="progress-bar bg-primary" style="width:{PCT_24}%"></div></div><span class="bar-value">{V_24} €</span></div>
                <div class="bar-row" onclick="showStatsPopup()"><div class="bar-label-container"><span class="bar-label-text" id="label-h-1">2025-26</span></div><div class="progress"><div class="progress-bar bg-danger" style="width:{PCT_CONS}%"></div></div><span class="bar-value">{V_CONS} €</span></div>
                <div class="bar-row" onclick="showStatsPopup()"><div class="bar-label-container"><span class="bar-label-text" id="label-h-2">Previsto</span></div><div class="progress"><div class="progress-bar bg-warning" style="width:{PCT_PROJ}%"></div></div><span class="bar-value">{V_PROJ} €</span></div>
            </div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr><th>Mese</th><th>2024-25</th><th>2025-26</th><th>Previsto</th><th class="col-small">Par.</th></tr></thead>
                <tbody id="table-body-home"></tbody>
                <tfoot><tr class="row-total"><td>Totali</td><td>{V_24}</td><td style="color:#b91c1c">{V_CONS}</td><td style="color:black">{V_PROJ}</td><td></td></tr></tfoot>
            </table>
            <div class="prediction-note">Previsioni basate su storico, stagionalità e trend attuale.</div>
            <div class="footer-note">Dati al {REF_DATE}</div>
        </div>
    </div>

    <div id="view-detail" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:80px; text-align:center;"><span onclick="showHome()" class="btn-styled">🏠</span></div>
                <div style="flex-grow:1; display:flex; justify-content:space-between; align-items:center;">
                    <div class="nav-arrow" onclick="changeView(-1)">&#10094;</div>
                    <h1 class="header-title" id="detail-title">MESE<br>ANNO</h1>
                    <div class="nav-arrow" onclick="changeView(1)">&#10095;</div>
                </div>
                <div style="width:80px; text-align:center;"><span onclick="printCurrentView()" class="btn-styled">🖨️</span></div>
            </div>
            <div class="total-box"><div class="total-amount" id="detail-total-display">0 €</div></div>
            <div class="chart-section" id="detail-chart"></div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr>
                    <th class="th-sortable" onclick="handleSortClick('month','day')"><span id="m-icon-day" class="sort-icon"></span>Giorno</th>
                    <th class="th-sortable" onclick="handleSortClick('month','cons')"><span id="m-icon-cons" class="sort-icon"></span>Consuntivo</th>
                    <th class="th-sortable" onclick="handleSortClick('month','prev')"><span id="m-icon-prev" class="sort-icon"></span>Previsto</th>
                </tr></thead>
                <tbody id="detail-table-body"></tbody>
            </table>
            <div class="footer-note">Dati al {REF_DATE}</div>
        </div>
    </div>

    <div id="view-day" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div class="nav-arrow" onclick="navDay(-1)">&#10094;</div>
                <div class="nav-arrow-up" onclick="closeDayDetail()">&#9650;</div>
                <h1 class="header-title" id="day-title" style="flex-grow:1;">GIORNO</h1>
                <div class="nav-arrow" onclick="navDay(1)">&#10095;</div>
                <span onclick="printCurrentView()" class="btn-styled" style="margin-left:10px;">🖨️</span>
            </div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr>
                    <th class="col-idx">#</th>
                    <th class="col-nom th-sortable" onclick="handleSortClick('day','nom')"><span id="icon-nom" class="sort-icon"></span>Nominativo</th>
                    <th class="col-imp th-sortable" onclick="handleSortClick('day','imp')"><span id="icon-imp" class="sort-icon"></span>Importo €</th>
                </tr></thead>
                <tbody id="day-table-body"></tbody>
            </table>
            <div style="background:#fff; padding:10px 20px; font-weight:bold; color:#555;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>Giorno:</span><span id="stats-day" style="color:black">0</span></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>Mese:</span><span id="stats-month" style="color:black">0</span></div>
                <div style="display:flex; justify-content:space-between;"><span>Anno:</span><span id="stats-year" style="color:black">0</span></div>
            </div>
        </div>
    </div>

    <div id="view-global" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:80px; text-align:center;"><span onclick="showHome()" class="btn-styled">🏠</span></div>
                <h1 class="header-title" style="flex-grow:1;">ANAGRAFICA</h1>
                <div style="width:80px; text-align:center;"><span onclick="printCurrentView()" class="btn-styled">🖨️</span></div>
            </div>
            <div class="search-container">
                <div style="position:relative; width:100%; max-width:400px;">
                    <input type="text" id="global-search" class="search-input" placeholder="Cerca..." oninput="filterGlobal(this.value)">
                    <span id="btn-clear-search" onclick="clearSearch()" style="position:absolute; right:10px; top:10px; cursor:pointer; display:none; color:red; font-weight:bold;">&#10005;</span>
                </div>
                <span id="global-filter-count" style="margin-left:10px; font-weight:bold; line-height:2.2;">(0)</span>
            </div>
        </div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr>
                    <th class="col-idx">#</th>
                    <th class="col-data th-sortable" onclick="handleSortClick('global','data')"><span id="g-icon-data" class="sort-icon"></span>Data</th>
                    <th class="col-nom th-sortable" onclick="handleSortClick('global','nom')"><span id="g-icon-nom" class="sort-icon"></span>Nominativo</th>
                    <th class="col-imp th-sortable" onclick="handleSortClick('global','imp')"><span id="g-icon-imp" class="sort-icon"></span>Importo</th>
                </tr></thead>
                <tbody id="global-table-body"></tbody>
                <tfoot><tr class="row-total"><td colspan="3" style="text-align:right">TOTALE:</td><td id="global-total-foot" style="color:black">0</td></tr></tfoot>
            </table>
        </div>
    </div>

    <div id="view-customer" style="display:none;">
        <div class="card-box">
            <div class="header-blue">
                <div style="width:100px; display:flex; gap:10px;">
                    <div class="nav-arrow" onclick="closeCustomer()">&#10094;</div>
                    <span onclick="copyCustomerData()" class="btn-styled" style="font-size:1.5rem; padding:2px 8px;">📋</span>
                </div>
                <h1 class="header-title" id="cust-title" style="flex-grow:1; font-size:1.8rem;">CLIENTE</h1>
                <div style="width:80px; text-align:center;"><span onclick="printCurrentView()" class="btn-styled">🖨️</span></div>
            </div>
        </div>
        <div id="cust-duplicates" class="dupe-box"><div style="color:#c2410c; font-weight:bold; margin-bottom:5px;">DUPLICATI:</div><div id="dupe-list"></div></div>
        <div class="card-box">
            <table class="table-custom">
                <thead><tr>
                    <th class="col-idx">#</th>
                    <th class="col-data th-sortable" onclick="handleSortClick('cust','data')"><span id="c-icon-data" class="sort-icon"></span>Data</th>
                    <th class="col-att th-sortable" onclick="handleSortClick('cust','att')"><span id="c-icon-att" class="sort-icon"></span>Attività</th>
                    <th class="col-imp th-sortable" onclick="handleSortClick('cust','imp')"><span id="c-icon-imp" class="sort-icon"></span>Importo</th>
                </tr></thead>
                <tbody id="cust-table-body"></tbody>
                <tfoot><tr class="row-total"><td colspan="3" style="text-align:right">TOTALE:</td><td id="cust-total-foot" style="color:black">0</td></tr></tfoot>
            </table>
        </div>
    </div>
    <div style="height:60px;"></div>
</div>
{JS}
</body>
</html>"""

CONTA_HTML = """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Monitor</title>
<style>body{margin:0;padding:20px;font-family:sans-serif;background:#e9edf5;display:flex;justify-content:center} .box{background:#fff;border-radius:12px;padding:20px;width:100%;max-width:600px;box-shadow:0 4px 15px rgba(0,0,0,0.1)} h1{text-align:center;color:#1F497D} table{width:100%;border-collapse:collapse} th,td{padding:10px;border-bottom:1px solid #eee} .num{font-weight:bold;color:#2563eb;float:right} .btn{background:#dc2626;color:white;border:none;padding:10px;width:100%;border-radius:8px;font-weight:bold;cursor:pointer;margin-bottom:20px} .btn-x{background:white;border:1px solid #ccc;color:#999;border-radius:4px;padding:2px 8px;float:right;cursor:pointer}</style></head>
<body><div class="box"><h1>📊 Monitor</h1><button class="btn" onclick="resetAll()">AZZERA TUTTO</button><table id="t"></table></div>
<script>
const API="https://countapi.mileshilliard.com/api/v1", NS="joyfit-stats-v1";
const PGS=[{id:'report_home',n:"Home"},{id:'report_global_list',n:"Anagrafica"},{id:'report_cust_detail',n:"Cliente"},...["SET","OTT","NOV","DIC","GEN","FEB","MAR","APR","MAG","GIU","LUG","AGO"].map(m=>({id:`report_${m}`,n:m}))];
const get=async u=>(await(await fetch(u)).json()).value||0; const set=async(i,v)=>fetch(`${API}/set/${NS}_${i}?value=${v}`);
async function load(){let h=""; for(let p of PGS){try{let v=await get(`${API}/get/${NS}_${p.id}`); h+=`<tr style="${v>0?'background:#f0f9ff':''}"><td>${p.n}</td><td><span class="num">${v}</span></td><td onclick="set('${p.id}',0);load()">❌</td></tr>`;}catch{}} document.getElementById('t').innerHTML=h;}
async function resetAll(){if(confirm("Sicuro?")) {await Promise.all(PGS.map(p=>set(p.id,0))); load();}}
load(); setInterval(load,5000);
</script></body></html>"""

# ================= GENERAZIONE =================
def build_report_html(json_data, t24, tCons, tProj, ref_date, is_admin):
    # Prepare Stats for Home Template
    max_v = max(t24, tProj) or 1
    
    html = HTML_TEMPLATE.replace("{CSS}", CSS_STYLES)
    html = html.replace("{JS}", JS_SCRIPT
                        .replace("DATA_PLACEHOLDER", json.dumps(json_data))
                        .replace("MESI_PLACEHOLDER", json.dumps(CONSTS["MESI"]))
                        .replace("IS_ADMIN_PLACEHOLDER", "true" if is_admin else "false"))
    
    html = html.replace("{ICON}", SETTINGS["ICON_URL"])
    html = html.replace("{TOT_HOME}", fmt_num(tProj))
    html = html.replace("{REF_DATE}", ref_date)
    
    html = html.replace("{V_24}", fmt_num(t24)).replace("{PCT_24}", str((t24/max_v)*100))
    html = html.replace("{V_CONS}", fmt_num(tCons)).replace("{PCT_CONS}", str((tCons/max_v)*100))
    html = html.replace("{V_PROJ}", fmt_num(tProj)).replace("{PCT_PROJ}", str((tProj/max_v)*100))
    
    return html

def main():
    print("Elaborazione Report JoyFit...")
    
    # 1. ETL
    monthly_d, daily_d = process_pdf_data()
    struct_csv, all_trans, dupes_map = process_csv_data()
    ref_date = load_ref_date(PATHS["DATE_FILE"]) or SETTINGS["DEFAULT_REF_DATE"]
    
    # 2. Logic Aggregation
    json_data, t24, tCons, tProj = prepare_json_data(monthly_d, daily_d, struct_csv, all_trans, dupes_map, ref_date)
    
    # 3. HTML Generation
    html_pub = build_report_html(json_data, t24, tCons, tProj, ref_date, False)
    html_adm = build_report_html(json_data, t24, tCons, tProj, ref_date, True)
    
    # 4. Save
    try:
        if not os.path.exists(PATHS["OUT_DIR"]): os.makedirs(PATHS["OUT_DIR"])
        
        with open(os.path.join(PATHS["OUT_DIR"], FILES["REPORT"]), "w", encoding="utf-8") as f: f.write(html_pub)
        with open(os.path.join(PATHS["OUT_DIR"], FILES["ADMIN"]), "w", encoding="utf-8") as f: f.write(html_adm)
        with open(os.path.join(PATHS["OUT_DIR"], FILES["CONTA"]), "w", encoding="utf-8") as f: f.write(CONTA_HTML)
        
        if os.path.exists(PATHS["BACKUP_DIR"]):
            with open(os.path.join(PATHS["BACKUP_DIR"], FILES["REPORT"]), "w", encoding="utf-8") as f: f.write(html_pub)
            
        print("Fatto. Apertura Admin...")
        webbrowser.open(f"file://{os.path.abspath(os.path.join(PATHS['OUT_DIR'], FILES['ADMIN']))}")
        
    except Exception as e: print(f"Errore Salvataggio: {e}")

if __name__ == "__main__":
    main()