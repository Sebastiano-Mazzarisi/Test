import pandas as pd
import datetime
import calendar
import numpy as np
import os
import json
import warnings
from difflib import SequenceMatcher
from decimal import Decimal, ROUND_HALF_UP

# Zittiamo i warning
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# --- CONFIGURAZIONE ---
FILE_DB = 'JF-DB.csv'
FILE_NORM = 'JF-Normalizza.csv'
FILE_HTML_OUT = 'JF-Report.html'

# Configurazione Link e Risorse
PDF_LOCAL_NAME = 'JF-Excel.pdf'
PDF_GITHUB_URL = 'https://sebastiano-mazzarisi.github.io/Test/JF-Excel.pdf'
IMG_ICON_URL = 'https://sebastiano-mazzarisi.github.io/Test/JoyFit.jpg' 
AUDIO_SINTESI_URL = 'https://sebastiano-mazzarisi.github.io/Test/Sintesi.mp3'

# Configurazione Contatori
COUNTER_NS = "joyfit-stats-v1"
COUNTER_BASE_URL = "https://countapi.mileshilliard.com/api/v1"

# Colori Standard
COL_BG_HEADER = "#1F497D" 
COL_BLUE = "#85c1e9"
COL_RED  = "#dc3545"
COL_GOLD = "#ffc107"
COL_YELLOW_BG = "#fff59d"
COL_RED_BG_LIGHT = "#ffe6e6"
COL_BORDER_GREY = "#bfbfbf"

# Colori Sintesi
COL_SINTESI_GREEN_BG = "#e8f5e9" 
COL_SINTESI_GREEN_TXT = "#2e7d32" 
COL_SINTESI_RED_BG = "#ffebee"    
COL_SINTESI_RED_TXT = "#c62828"   
COL_BARRA_RIEPILOGO = "#455a64"   
COL_SINTESI_SINGLE_BG = "#e6f2ff" # Azzurro tenue

# --- TITOLI AGGIORNATI ---
TITOLI_TABELLE = {
    '0': "Sintesi", 
    '1': "1. Riepilogo",
    '2': "2. Contanti",
    '3': "3. POS",
    '4': "4. Entrate X",
    '5': "5. Clienti",
    '6': "6. Spesa Media",
    '7': "7. Orari",
    '8': "8. Giorni",
    '9': "9. Attività",
    '10': "10. Clienti Top 100",
    '11': "11. Clienti Attesi",
    '12': "12. Clienti da Chiamare"
}

# --- DESCRIZIONI AGGIORNATE ---
DESCRIZIONI_TABELLE = {
    '0': "I numeri che parlano",
    '1': "Mostra l’andamento complessivo degli incassi mese per mese tra anno precedente, anno corrente e previsione finale basata sull’andamento reale e pesi settimanali.",
    '2': "Evidenzia la parte di incasso proveniente esclusivamente dai pagamenti in contanti. Utile per valutare il peso della cassa rispetto al totale.",
    '3': "Mostra gli incassi derivanti dai pagamenti elettronici tramite POS. Indica la quota digitale del fatturato.",
    '4': "Raccoglie gli incassi attribuiti a clienti non registrati o ingressi occasionali. Serve per stimare il peso del ‘non ricorrente’.",
    '5': "Indica il numero di clienti unici attivi mese per mese, confrontando anno Precedente, anno Corrente e una Previsione automatica basata sugli anni precedenti.",
    '6': "Calcola la media di spesa per cliente dividendo l’incasso totale per il numero di clienti unici. Misura la qualità della spesa.",
    '7': "Mostra quanto incasso è stato generato la MATTINA (Sabina) e nel POMERIGGIO-SERA (Marica). Aiuta a capire come distribuire le attività di segreteria.",
    '8': "Classifica gli incassi in base ai giorni, per individuare picchi e debolezze settimanali.",
    '9': "Ordina le attività in base al totale incassato, mostrando quali corsi trainano e quali rendono meno.",
    '10': "Elenca i 100 clienti che hanno speso di più nell’anno corrente, con numero pagamenti e totale acquistato.",
    '11': "Mostra i clienti presenti l’anno precedente ma non tornati quest’anno, con totale pagamenti e spesa associata.",
    '12': "Indica i clienti presenti in tutti gli ultimi anni ma assenti quest’anno. Segnala cali strutturali della clientela più fedele."
}

ord_m = ['Settembre', 'Ottobre', 'Novembre', 'Dicembre', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto']
map_m = {1:'Gennaio', 2:'Febbraio', 3:'Marzo', 4:'Aprile', 5:'Maggio', 6:'Giugno', 7:'Luglio', 8:'Agosto', 9:'Settembre', 10:'Ottobre', 11:'Novembre', 12:'Dicembre'}

# --- FUNZIONI CALCOLO ---
def clean_field(val):
    if val is None: return ""
    s = str(val).strip().lower()
    if s in ["nan", "none", "null", "0", "0.0", "0,0", "false", "-", ".", ""]: return ""
    return str(val).strip()

def normalize_name(val):
    s = clean_field(val)
    if not s: return ""
    return " ".join(s.split()).title()

def parse_strict_money(val):
    try:
        s = str(val).replace(',', '.').strip()
        if not s or s.lower() in ['nan', 'none', '-', '']:
            return 0.0
        d = Decimal(s).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(d)
    except:
        return 0.0

def calcola_pesi_settimanali_mediana(df, tipo='incasso'):
    if tipo == 'incasso':
        df_v = df[df['Totale'] >= 0]
        if df_v.empty: return {i:1.0 for i in range(7)}
        med = df_v.groupby(df_v['Data'].dt.weekday)['Totale'].median().to_dict()
    elif tipo == 'clienti':
        daily = df.groupby('Data')['Nominativo'].nunique()
        med = daily.groupby(daily.index.dayofweek).median().to_dict()
    for i in range(7): 
        if i not in med: med[i] = 0.0
    return med

def calcola_proiezione_data_driven(reale, data_rif, pesi):
    y, m, d = data_rif.year, data_rif.month, data_rif.day
    tot_days = calendar.monthrange(y, m)[1]
    passato, totale = 0.0, 0.0
    for day in range(1, tot_days+1):
        wd = datetime.date(y, m, day).weekday()
        p = pesi.get(wd, 0)
        totale += p
        if day <= d: passato += p
    if passato == 0: return reale
    ratio = reale / passato
    if (tot_days - d) <= 3: ratio = 1.0
    proj = reale + (ratio * (totale - passato))
    return int(max(reale, proj))

def calcola_previsioni_ibride(df_pivot, anno_curr, data_rif, pesi):
    anni_hist = sorted([c for c in df_pivot.columns if c != anno_curr], reverse=True)[:3]
    pesi_use = [0.9, 0.8, 0.7][:len(anni_hist)]
    map_idx = {9:0, 10:1, 11:2, 12:3, 1:4, 2:5, 3:6, 4:7, 5:8, 6:9, 7:10, 8:11}
    idx_curr = map_idx.get(data_rif.month, 0)
    base = {}
    for m in ord_m:
        n, d = 0, 0
        if m in df_pivot.index:
            for i, a in enumerate(anni_hist):
                v = df_pivot.loc[m, a]
                if v > 0: n += v * pesi_use[i]; d += pesi_use[i]
        base[m] = n/d if d>0 else 0
    trend_n, trend_d = 0, 0
    for i in range(idx_curr):
        m = ord_m[i]
        if m in df_pivot.index:
            r = df_pivot.loc[m, anno_curr]
            s = base[m]
            if r>0 and s>0: trend_n += r; trend_d += s
    tf = trend_n / trend_d if trend_d > 0 else 1.0
    if tf > 1.3: tf = 1.3
    if tf < 0.7: tf = 0.7
    col_p = []
    for m in df_pivot.index:
        try: idx = ord_m.index(m)
        except: idx = -1
        real = df_pivot.loc[m, anno_curr] if anno_curr in df_pivot.columns else 0
        if idx < idx_curr: col_p.append(real)
        elif idx == idx_curr:
            proj = calcola_proiezione_data_driven(real, data_rif, pesi)
            col_p.append(max(real, proj))
        else:
            b = base.get(m, 0)
            col_p.append(int(b * tf))
    df_pivot['Previsioni'] = col_p
    return df_pivot

def calcola_moltiplicatore_clienti_unici(df, anno_curr, mese_limite):
    anni = [a for a in df['AnnoSportivo'].unique() if a != anno_curr]
    rapporti = []
    ord_mesi_num = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]
    try: idx_lim = ord_mesi_num.index(mese_limite)
    except: idx_lim = len(ord_mesi_num)-1
    mesi_incl = ord_mesi_num[:idx_lim+1]
    for a in anni:
        d_a = df[df['AnnoSportivo'] == a]
        if d_a.empty: continue
        tot_final = d_a[d_a['Nominativo']!=""]['Nominativo'].nunique()
        d_ytd = d_a[d_a['Data'].dt.month.isin(mesi_incl)]
        ytd_val = d_a[d_a['Data'].dt.month.isin(mesi_incl) & (d_a['Nominativo']!="")]["Nominativo"].nunique()
        if ytd_val > 0: rapporti.append(tot_final / ytd_val)
    return sum(rapporti) / len(rapporti) if rapporti else 1.0

def get_pivot_with_total(df, idx, col, val):
    p = df.pivot_table(index=idx, columns=col, values=val, aggfunc='sum', fill_value=0)
    p['Totali'] = p.sum(axis=1)
    return p.sort_values('Totali', ascending=False)

def get_top10_historical(df, grp):
    mask = (~df[grp].astype(str).str.contains("Totale|Riepilogo|Marica|Sabina", case=False)) & (df[grp]!="")
    df_clean = df[mask].copy()
    if grp == 'Nominativo':
        df_clean[grp] = df_clean[grp].apply(lambda x: x.split()[0] if len(x.split())>0 else x)
    top = df_clean.groupby(grp)['Totale'].sum().sort_values(ascending=False).head(10).index
    df_t = df_clean[df_clean[grp].isin(top)]
    p = df_t.pivot_table(index=grp, columns='AnnoSportivo', values='Totale', aggfunc='sum', fill_value=0)
    p['Totali'] = p.sum(axis=1)
    return p.sort_values('Totali', ascending=False)

def accorpa_nomi_simili(df_stats):
    df = df_stats.reset_index()
    df = df.sort_values(by='Volte', ascending=False)
    nomi_processati = []
    mappa_nomi = {} 
    for nome in df['Nominativo']:
        trovato = False
        for esistente in nomi_processati:
            ratio = SequenceMatcher(None, nome, esistente).ratio()
            if ratio > 0.90: 
                mappa_nomi[nome] = esistente
                trovato = True
                break
        if not trovato:
            nomi_processati.append(nome)
            mappa_nomi[nome] = nome
    df_out = df.groupby('Nominativo').agg({'Volte': 'sum','Totali': 'sum'})
    df_out['Totali'] = df_out['Totali'].round(2)
    return df_out

# --- FUNZIONI EXTRA PER CALENDARIO ---
def is_holiday(date_obj):
    # Domenica = 6
    if date_obj.weekday() == 6: return True
    # Festività Fisse Italiane Invernali/Standard
    d, m = date_obj.day, date_obj.month
    festivi = [(8, 12), (25, 12), (26, 12), (1, 1), (6, 1), (15, 8)]
    if (d, m) in festivi: return True
    return False

def get_calendar_data(df, year, month):
    # Filtra DF per mese corrente
    mask = (df['Data'].dt.year == year) & (df['Data'].dt.month == month)
    df_m = df[mask].copy()
    
    # Raggruppa per giorno
    daily_inc = df_m.groupby(df_m['Data'].dt.day)['Totale'].sum().to_dict()
    
    tot_days = calendar.monthrange(year, month)[1]
    cal_list = []
    
    running_total = 0
    prev_d = 0 # per tracciare i buchi
    
    # Mapping giorni abbreviati
    giorni_it = ['Lu', 'Ma', 'Me', 'Gi', 'Ve', 'Sa', 'Do']
    
    for d in range(1, tot_days + 1):
        dt = datetime.date(year, month, d)
        
        if not is_holiday(dt):
            val = daily_inc.get(d, 0)
            running_total += val
            
            # Se val == 0, stringa vuota, altrimenti formatta
            val_str = f"{val:,.0f} €".replace(",", "X").replace(".", ",").replace("X", ".") if val > 0 else ""
            
            # Controllo "Salto" (Gap)
            gap = False
            if prev_d > 0 and (d > prev_d + 1):
                gap = True
            
            cal_list.append({
                "day": d, 
                "wday": giorni_it[dt.weekday()], # Aggiunto Giorno Settimana
                "val": val_str,
                "gap": gap
            })
            prev_d = d
            
    # Totale formattato
    total_str = f"{running_total:,.0f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    
    return {"rows": cal_list, "total": total_str}

# --- GENERATORE HTML ---
def format_number(val):
    if pd.isna(val) or val == 0: return "" 
    if isinstance(val, (int, float)):
        val = round(val)
    return "{:,.0f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")

def generate_rows_html(df, key_tab, ap, ac, current_date, is_currency=True):
    html = ""
    
    if key_tab in ['10', '11', '12']:
        wrapper_id = f"list-wrapper-{key_tab}"
        html += f'''
        <div class="header-row header-row-11">
            <span class="col-prog"></span>
            <span class="col-name" onclick="sortTable('{wrapper_id}', 'name')" style="cursor:pointer;">Cliente <span class="sort-arrow" id="sort-arrow-name">▼</span></span>
            <span class="col-freq" onclick="sortTable('{wrapper_id}', 'volte')" style="cursor:pointer;">Volte <span class="sort-arrow" id="sort-arrow-volte">▼</span></span>
            <span class="col-money" onclick="sortTable('{wrapper_id}', 'amount')" style="cursor:pointer;">Totale<div class="euro-sub">(€) <span class="sort-arrow sort-active" id="sort-arrow-amount">▼</span></div></span>
        </div>
        <div id="{wrapper_id}">'''
        
        df_sorted = df.sort_values('Totali', ascending=False)
        count = 1
        for idx, row in df_sorted.iterrows():
            val_volte = row['Volte']
            val_tot = row['Totali']
            html += f'''
            <div class="data-row-4col" data-name="{idx}" data-volte="{int(val_volte)}" data-amount="{val_tot}">
                <span class="col-prog">{count}</span>
                <span class="col-name">{idx}</span>
                <span class="col-freq">{int(val_volte)}</span>
                <span class="col-money">{format_number(val_tot)}</span>
            </div>'''
            count += 1
        html += '</div>'
        return html

    is_temporal = int(key_tab) <= 6
    if is_temporal:
        curr_m_name = map_m[current_date.month]
        try: curr_m_idx = ord_m.index(curr_m_name)
        except: curr_m_idx = -1
        sub_curr = '<div class="euro-sub">(€)</div>' if is_currency else '<div class="euro-sub">&nbsp;</div>'
        html += f'''
        <div class="header-row">
            <span class="col-lbl"></span>
            <span class="col-val">{ap}{sub_curr}</span>
            <span class="col-val">{ac}{sub_curr}</span>
            <span class="col-val">Previsto{sub_curr}</span>
        </div>'''
        for i, m in enumerate(df.index):
            val_ap = df.loc[m, ap] if ap in df.columns else 0
            val_ac = df.loc[m, ac] if ac in df.columns else 0
            val_pr = df.loc[m, 'Previsioni'] if 'Previsioni' in df.columns else 0
            
            style_ap = f"background-color: {COL_SINTESI_SINGLE_BG}; border-bottom: 1px solid {COL_BORDER_GREY};"
            style_prev = ""
            if i >= curr_m_idx:
                style_prev = f"background-color: {COL_YELLOW_BG}; font-weight:bold; border-bottom: 1px solid {COL_BORDER_GREY};"
            style_curr = f"font-weight:bold; border-bottom: 1px solid {COL_BORDER_GREY};"
            if val_ac > 0:
                style_curr = f"background-color: {COL_RED_BG_LIGHT}; font-weight:bold; border-bottom: 1px solid {COL_BORDER_GREY};"
            str_ac = format_number(val_ac)
            
            html += f'''
            <div class="data-row-3col">
                <span class="col-lbl">{m[:3]}</span>
                <span class="col-val" style="{style_ap}">{format_number(val_ap)}</span>
                <span class="col-val" style="{style_curr}">{str_ac}</span>
                <span class="col-val" style="{style_prev}">{format_number(val_pr)}</span>
            </div>'''
    return html

def generate_chart_html(df, key_tab, anno_prec, anno_curr, is_temporal=True, is_currency=True, is_wide_label=False):
    title_html = '<div class="chart-title">Analisi Grafica</div>' if not is_wide_label else ''
    html = f'<div class="chart-container">{title_html}'
    data_points = []
    
    if key_tab in ['10', '11', '12']:
        df_sort = df.sort_values('Totali', ascending=False).head(10)
        for i, (idx, row) in enumerate(df_sort.iterrows()):
            color = COL_RED if i == 0 else COL_BLUE
            data_points.append({"lbl": str(idx), "val": row['Totali'], "col": color})
            
    elif is_temporal:
        val_prec = df[anno_prec].sum() if anno_prec in df.columns else 0
        val_curr = df[anno_curr].sum() if anno_curr in df.columns else 0
        val_prev = df['Previsioni'].sum() if 'Previsioni' in df.columns else 0
        if val_prec > 0: data_points.append({"lbl": anno_prec, "val": val_prec, "col": COL_BLUE})
        if val_curr > 0: data_points.append({"lbl": anno_curr, "val": val_curr, "col": COL_RED})
        if val_prev > 0: data_points.append({"lbl": "Previsto", "val": val_prev, "col": COL_GOLD})
    else:
        col_target = 'Totali' if 'Totali' in df.columns else df.columns[-1]
        df_sorted = df.sort_values(col_target, ascending=False).head(10)
        for i, (idx, row) in enumerate(df_sorted.iterrows()):
            color = COL_RED if i == 0 else COL_BLUE
            data_points.append({"lbl": str(idx), "val": row[col_target], "col": color})

    if not data_points: return ""
    max_val = max([d['val'] for d in data_points]) if data_points else 1
    suffix = " €" if is_currency else ""
    lbl_class = "chart-lbl-wide" if is_wide_label else "chart-lbl"
    
    custom_lbl_width = "70px"
    if is_wide_label: custom_lbl_width = "165px"
        
    if key_tab == '7': custom_lbl_width = "80px"
    elif key_tab == '8': custom_lbl_width = "80px"
    elif key_tab == '9': custom_lbl_width = "130px"

    for i, dp in enumerate(data_points):
        pct = (dp['val'] / max_val) * 100
        if pct < 1: pct = 1
        html += f'''
        <div class="chart-row">
            <div class="{lbl_class}" style="width: {custom_lbl_width} !important;">{dp['lbl']}</div>
            <div class="chart-bar-area"><div class="chart-bar" style="width:{pct}%; background-color: {dp['col']};"></div></div>
            <div class="chart-val">{format_number(dp['val'])}{suffix}</div>
        </div>'''
    html += '</div>'
    return html

# --- MAIN ---

def genera_app():
    print("--- GENERAZIONE REPORT ---")
    if not os.path.exists(FILE_DB): return

    if os.path.exists(PDF_LOCAL_NAME): FINAL_LINK = PDF_LOCAL_NAME
    else: FINAL_LINK = PDF_GITHUB_URL
    FINAL_LINK_JS = FINAL_LINK.replace('\\', '/')

    df = pd.read_csv(FILE_DB, encoding='utf-8')
    for c in ['CassaX', 'Registrato', 'Nominativo']:
        if c not in df.columns: df[c] = ''
        df[c] = df[c].apply(clean_field)
    df['Nominativo'] = df['Nominativo'].apply(normalize_name)
    
    if os.path.exists(FILE_NORM):
        try:
            nd = pd.read_csv(FILE_NORM, encoding='utf-8')
            d = dict(zip(nd['Attività'].astype(str).str.strip(), nd['Normalizzata'].astype(str).str.strip()))
            df['Attività'] = df['Attività'].astype(str).str.strip().map(d).fillna(df['Attività'])
        except: pass

    df.columns = df.columns.str.strip()
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    
    for c in ['Contanti', 'Pos', 'Uscite']: 
        if c in df.columns: 
            df[c] = df[c].apply(parse_strict_money)
            
    df['Totale'] = (df['Contanti'] + df['Pos']).round(2)
    
    dm = df['Data'].max()
    if pd.isna(dm): dm = datetime.datetime.now()
    
    def get_as(d): return f"{d.year}-{str(d.year+1)[-2:]}" if d.month >= 9 else f"{d.year-1}-{str(d.year)[-2:]}"
    df['AnnoSportivo'] = df['Data'].apply(get_as)
    df['MeseAbbr'] = df['Data'].dt.month.map(map_m)
    anni = sorted(df['AnnoSportivo'].unique())
    ac = anni[-1] if anni else "N/D"
    ap = anni[-2] if len(anni) > 1 else "N/D"

    pesi_inc = calcola_pesi_settimanali_mediana(df, 'incasso')
    pesi_cli = calcola_pesi_settimanali_mediana(df, 'clienti')

    p_mesi = calcola_previsioni_ibride(df.pivot_table(index='MeseAbbr', columns='AnnoSportivo', values='Totale', aggfunc='sum', fill_value=0).reindex([m for m in ord_m if m in df['MeseAbbr'].unique()]), ac, dm, pesi_inc)
    p_cont = calcola_previsioni_ibride(df.pivot_table(index='MeseAbbr', columns='AnnoSportivo', values='Contanti', aggfunc='sum', fill_value=0).reindex([m for m in ord_m if m in df['MeseAbbr'].unique()]), ac, dm, pesi_inc)
    p_pos = calcola_previsioni_ibride(df.pivot_table(index='MeseAbbr', columns='AnnoSportivo', values='Pos', aggfunc='sum', fill_value=0).reindex([m for m in ord_m if m in df['MeseAbbr'].unique()]), ac, dm, pesi_inc)
    
    mask_x = (df['Registrato'] == "")
    df_x = df[mask_x].copy()
    if df_x.empty: p_x = pd.DataFrame(columns=[ac], index=ord_m).fillna(0); p_x['Previsioni'] = 0
    else: p_x = calcola_previsioni_ibride(df_x.pivot_table(index='MeseAbbr', columns='AnnoSportivo', values='Totale', aggfunc='sum', fill_value=0).reindex([m for m in ord_m if m in df_x['MeseAbbr'].unique()]), ac, dm, calcola_pesi_settimanali_mediana(df_x, 'incasso'))

    p_cli = calcola_previsioni_ibride(df[df['Nominativo']!=""].pivot_table(index='MeseAbbr', columns='AnnoSportivo', values='Nominativo', aggfunc='nunique', fill_value=0).reindex([m for m in ord_m if m in df['MeseAbbr'].unique()]), ac, dm, pesi_cli)
    ci = p_mesi.columns.intersection(p_cli.columns)
    p_avg = p_mesi[ci].div(p_cli[ci]).replace([np.inf, -np.inf], 0).fillna(0)

    def clean_op(op):
        s = str(op).lower(); 
        if "marica" in s: return "Marica"
        if "sabina" in s: return "Sabina"
        return "Altri"
    df['OpGroup'] = df['Operatore'].apply(clean_op)
    p_ops = get_pivot_with_total(df, 'OpGroup', 'AnnoSportivo', 'Totale')
    map_g = {0:"Lun", 1:"Mar", 2:"Mer", 3:"Gio", 4:"Ven", 5:"Sab", 6:"Dom"}
    ord_g = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    df['Giorno'] = df['Data'].dt.weekday.map(map_g) 
    p_w = get_pivot_with_total(df, 'Giorno', 'AnnoSportivo', 'Totale').reindex([g for g in ord_g if g in df['Giorno'].unique()])
    
    df_ta = get_top10_historical(df, 'Attività')

    # --- CALCOLO CLIENTI LISTE ---
    df_clean_names = df[df['Nominativo'].str[0].str.isupper().fillna(False)]
    try: idx_ac = anni.index(ac)
    except: idx_ac = 0

    df_curr_ac = df_clean_names[(df_clean_names['AnnoSportivo'] == ac) & (df_clean_names['Nominativo']!="")]
    df_top_raw = df_curr_ac.groupby('Nominativo').agg(Volte=('Data', 'count'), Totali=('Totale', 'sum'))
    df_top_raw = df_top_raw[df_top_raw['Totali'] > 0]
    df_tc = accorpa_nomi_simili(df_top_raw).sort_values('Totali', ascending=False)

    df_ap = df_clean_names[(df_clean_names['AnnoSportivo'] == ap) & (df_clean_names['Nominativo']!="")]
    cli_ap = set(df_ap['Nominativo'].unique())
    df_ac = df_clean_names[(df_clean_names['AnnoSportivo'] == ac) & (df_clean_names['Nominativo']!="")]
    cli_ac = set(df_ac['Nominativo'].unique())
    cli_lost = cli_ap - cli_ac
    movimenti_persi = df_ap[df_ap['Nominativo'].isin(cli_lost)].shape[0]
    df_lost_raw = df_ap[df_ap['Nominativo'].isin(cli_lost)].groupby('Nominativo').agg(Volte=('Data', 'count'), Totali=('Totale', 'sum'))
    df_lost_raw = df_lost_raw[df_lost_raw['Totali'] > 0]
    df_lost_stats = accorpa_nomi_simili(df_lost_raw).sort_index()
    
    num_anni_storici = 4 
    start_idx = max(0, idx_ac - num_anni_storici)
    anni_strict_check = anni[start_idx:idx_ac] 
    cli_fedeli_lost = set()
    if anni_strict_check:
        primo_anno = anni_strict_check[0]
        cli_fedeli_candidate = set(df_clean_names[df_clean_names['AnnoSportivo'] == primo_anno]['Nominativo'].unique())
        for y in anni_strict_check[1:]:
            c_y = set(df_clean_names[df_clean_names['AnnoSportivo'] == y]['Nominativo'].unique())
            cli_fedeli_candidate = cli_fedeli_candidate.intersection(c_y)
        cli_fedeli_lost = cli_fedeli_candidate - cli_ac

    df_past_all = df_clean_names[(df_clean_names['AnnoSportivo'] != ac) & (df_clean_names['Nominativo']!="")]
    if not cli_fedeli_lost:
         df_fedeli_stats = pd.DataFrame(columns=['Volte', 'Totali'])
    else:
         df_fedeli_raw = df_past_all[df_past_all['Nominativo'].isin(cli_fedeli_lost)].groupby('Nominativo').agg(Volte=('Data', 'count'), Totali=('Totale', 'sum'))
         df_fedeli_raw = df_fedeli_raw[df_fedeli_raw['Totali'] > 0]
         df_fedeli_stats = accorpa_nomi_simili(df_fedeli_raw).sort_index()

    df_pdf_top = df_tc.reset_index().sort_values('Totali', ascending=False)
    raw_pdf_top = []
    for _, row in df_pdf_top.iterrows():
        raw_pdf_top.append({"name": row['Nominativo'], "volte": int(row['Volte']), "tot": row['Totali']})
    pdf_data_10_json = json.dumps(raw_pdf_top)

    df_pdf_lost = df_lost_stats.reset_index().sort_values('Totali', ascending=False)
    raw_pdf_lost = []
    for _, row in df_pdf_lost.iterrows():
        raw_pdf_lost.append({"name": row['Nominativo'], "volte": int(row['Volte']), "tot": row['Totali']})
    pdf_data_11_json = json.dumps(raw_pdf_lost)
    
    df_pdf_fed = df_fedeli_stats.reset_index().sort_values('Totali', ascending=False)
    raw_pdf_fed = []
    for _, row in df_pdf_fed.iterrows():
        raw_pdf_fed.append({"name": row['Nominativo'], "volte": int(row['Volte']), "tot": row['Totali']})
    pdf_data_12_json = json.dumps(raw_pdf_fed)
    
    DATA_STORE = {'0': pd.DataFrame(), '1': p_mesi, '2': p_cont, '3': p_pos, '4': p_x, '5': p_cli, '6': p_avg, '7': p_ops, '8': p_w, '9': df_ta, '10': df_tc, '11': df_lost_stats, '12': df_fedeli_stats}

    cli_tot_ac = df[(df['AnnoSportivo'] == ac) & (df['Nominativo']!="")]["Nominativo"].nunique()
    cli_tot_ap = df[(df['AnnoSportivo'] == ap) & (df['Nominativo']!="")]["Nominativo"].nunique()
    mult_cli = calcola_moltiplicatore_clienti_unici(df, ac, dm.month)
    cli_tot_prev = int(cli_tot_ac * mult_cli)
    if cli_tot_prev < cli_tot_ac: cli_tot_prev = cli_tot_ac
    
    inc_tot_ac = p_mesi[ac].sum() if ac in p_mesi.columns else 0
    inc_tot_prev = p_mesi['Previsioni'].sum() if 'Previsioni' in p_mesi.columns else 0
    inc_tot_ap = p_mesi[ap].sum() if ap in p_mesi.columns else 0
    avg_tot_ac = inc_tot_ac / cli_tot_ac if cli_tot_ac > 0 else 0
    avg_tot_prev = inc_tot_prev / cli_tot_prev if cli_tot_prev > 0 else 0
    avg_tot_ap = inc_tot_ap / cli_tot_ap if cli_tot_ap > 0 else 0
    
    top_count = len(df_tc); top_sum = df_tc['Totali'].sum()
    lost_count = len(df_lost_stats); lost_sum = df_lost_stats['Totali'].sum()
    fedeli_count = len(df_fedeli_stats); fedeli_sum = df_fedeli_stats['Totali'].sum()
    last_update_str = dm.strftime('%d/%m/%Y')
    
    # --- Preparazione Dati Calendario DOPPIO ---
    # 1. Anno Corrente
    cal_curr = get_calendar_data(df, dm.year, dm.month)
    title_curr = f"{map_m[dm.month].upper()} {dm.year}"
    
    # 2. Anno Precedente (Stesso mese)
    prev_year = dm.year - 1
    cal_prev = get_calendar_data(df, prev_year, dm.month)
    title_prev = f"{map_m[dm.month].upper()} {prev_year}"
    
    cal_data_curr_json = json.dumps(cal_curr)
    cal_data_prev_json = json.dumps(cal_prev)

    curr_month_name = map_m[dm.month]
    try: curr_idx_ord = ord_m.index(curr_month_name)
    except: curr_idx_ord = 0
    months_ytd = ord_m[:curr_idx_ord+1]

    json_data = []
    lista_chiavi = sorted(TITOLI_TABELLE.keys(), key=lambda x: int(x))
    
    # ARRAY PER RACCOGLIERE I DATI DELLA SINTESI PER IL PDF
    raw_sintesi_data = []
    
    menu_html = '<div id="menu-view">'
    details_html = ''
    
    for idx, key in enumerate(lista_chiavi):
        title = TITOLI_TABELLE[key]
        df_curr = DATA_STORE[key]
        json_data.append({"id": f"tab_{idx}", "title": title, "date": ""})
        
        # --- FIX TRIGGER: Torna a loadTable(0) normale, la generazione PDF è nell'header interno
        if key == '0':
            menu_style = f'style="justify-content: center; text-align: center; border: 3px solid {COL_BG_HEADER}; border-radius: 10px; margin: 5px 15px; height: 75px;"'
            menu_html += f'<div class="menu-item" id="menu-item-{idx}" onclick="loadTable({idx})" {menu_style}>{title}</div>'
        else:
            menu_html += f'<div class="menu-item" id="menu-item-{idx}" onclick="loadTable({idx})">{title}</div>'
        
        delta_html = ""
        desc_text = DESCRIZIONI_TABELLE.get(key, "")
        
        content_block = ""
        
        if key == '0':
            config_sintesi = [
                {'k': '1', 'label': '1. RIEPILOGO INCASSI'},
                {'k': '2', 'label': '2. CONTANTI'},
                {'k': '3', 'label': '3. POS'},
                {'k': '4', 'label': '4. ENTRATE X'},
                {'k': '5', 'label': '5. CLIENTI'},
                {'k': '6', 'label': '6. SPESA MEDIA'},
                {'k': '7', 'label': '7. ORARI'},
                {'k': '8', 'label': '8. GIORNI'},
                {'k': '9', 'label': '9. ATTIVITA\''},
                {'k': '10', 'label': '10. CLIENTI TOP 100'},
                {'k': '11', 'label': '11. CLIENTI ATTESI'},
                {'k': '12', 'label': '12. CLIENTI DA CHIAMARE'},
            ]

            content_block = '<div style="margin-top:10px;">'
            for item in config_sintesi:
                k_ref = item['k']
                label_block = item['label']
                df_ref = DATA_STORE[k_ref]
                
                if k_ref in ['1', '2', '3', '4', '5', '6']:
                    is_curr_block = (k_ref != '5') 
                    
                    if k_ref == '5': 
                         mask_ap_ytd = (df['AnnoSportivo'] == ap) & (df['MeseAbbr'].isin(months_ytd)) & (df['Nominativo'] != "")
                         fm_ap_ref = df.loc[mask_ap_ytd, 'Nominativo'].nunique()
                         mask_ac_ytd = (df['AnnoSportivo'] == ac) & (df['MeseAbbr'].isin(months_ytd)) & (df['Nominativo'] != "")
                         fm_prev_ref = df.loc[mask_ac_ytd, 'Nominativo'].nunique()
                         mask_ap_total = (df['AnnoSportivo'] == ap) & (df['Nominativo'] != "")
                         fa_ap_ref = df.loc[mask_ap_total, 'Nominativo'].nunique()
                         fa_prev_ref = cli_tot_prev 

                    elif k_ref == '6': 
                         mask_ap_ytd = (df['AnnoSportivo'] == ap) & (df['MeseAbbr'].isin(months_ytd))
                         inc_ap_ytd = df.loc[mask_ap_ytd, 'Totale'].sum()
                         mask_ac_ytd = (df['AnnoSportivo'] == ac) & (df['MeseAbbr'].isin(months_ytd))
                         inc_ac_ytd = df.loc[mask_ac_ytd, 'Totale'].sum()
                         cli_ap_ytd = df.loc[mask_ap_ytd & (df['Nominativo']!=""), 'Nominativo'].nunique()
                         cli_ac_ytd = df.loc[mask_ac_ytd & (df['Nominativo']!=""), 'Nominativo'].nunique()
                         fm_ap_ref = inc_ap_ytd / cli_ap_ytd if cli_ap_ytd > 0 else 0
                         fm_prev_ref = inc_ac_ytd / cli_ac_ytd if cli_ac_ytd > 0 else 0
                         
                         mask_ap_tot = (df['AnnoSportivo'] == ap)
                         inc_ap_tot = df.loc[mask_ap_tot, 'Totale'].sum()
                         cli_ap_tot = df.loc[mask_ap_tot & (df['Nominativo']!=""), 'Nominativo'].nunique()
                         fa_ap_ref = inc_ap_tot / cli_ap_tot if cli_ap_tot > 0 else 0
                         fa_prev_ref = inc_tot_prev / cli_tot_prev if cli_tot_prev > 0 else 0
                    
                    else:
                        valid_months_ref = [m for m in months_ytd if m in df_ref.index]
                        if valid_months_ref:
                            fm_prev_ref = df_ref.loc[valid_months_ref, 'Previsioni'].sum() if 'Previsioni' in df_ref.columns else 0
                            fm_ap_ref = df_ref.loc[valid_months_ref, ap].sum() if ap in df_ref.columns else 0
                        else:
                            fm_prev_ref = 0; fm_ap_ref = 0
                        fa_prev_ref = df_ref['Previsioni'].sum() if 'Previsioni' in df_ref.columns else 0
                        fa_ap_ref = df_ref[ap].sum() if ap in df_ref.columns else 0

                    diff_fm_ref = fm_prev_ref - fm_ap_ref
                    pct_fm_ref = (diff_fm_ref / fm_ap_ref * 100) if fm_ap_ref > 0 else 0
                    sign_fm_ref = "+" if diff_fm_ref >= 0 else ""
                    class_fm_ref = "green" if diff_fm_ref >= 0 else "red"

                    diff_fa_ref = fa_prev_ref - fa_ap_ref
                    pct_fa_ref = (diff_fa_ref / fa_ap_ref * 100) if fa_ap_ref > 0 else 0
                    sign_fa_ref = "+" if diff_fa_ref >= 0 else ""
                    class_fa_ref = "green" if diff_fa_ref >= 0 else "red"
                    
                    sym = " €" if is_curr_block else ""
                    
                    # MODIFICA: Creazione HTML per simbolo Euro piccolo
                    val_suffix_html = '<span style="font-size:0.5em; vertical-align: text-top;">€</span>' if is_curr_block else ""
                    
                    pct_fm_str = f"{pct_fm_ref:.1f}".replace('.', ',')
                    pct_fa_str = f"{pct_fa_ref:.1f}".replace('.', ',')
                    
                    # SALVATAGGIO DATI PER PDF (Tipo Comp)
                    curr_suffix_pdf = " €" if k_ref != '5' else ""
                    
                    raw_sintesi_data.append({
                        "type": "comp",
                        "title": label_block,
                        "v1": f"{sign_fm_ref} {format_number(diff_fm_ref)}{curr_suffix_pdf}",
                        "p1": f"{sign_fm_ref} {pct_fm_str}%",
                        "t1": f"Totale {format_number(fm_prev_ref)}{curr_suffix_pdf}",
                        "v2": f"{sign_fa_ref} {format_number(diff_fa_ref)}{curr_suffix_pdf}",
                        "p2": f"{sign_fa_ref} {pct_fa_str}%",
                        "t2": f"Totale {format_number(fa_prev_ref)}{curr_suffix_pdf}"
                    })

                    content_block += f'''
                    <div style="margin-bottom:25px;">
                        <div class="sintesi-header-bar">{label_block}</div>
                        <div class="sintesi-grid">
                            <div class="sintesi-box-detail {class_fm_ref}">
                                <div class="sintesi-val-det">{sign_fm_ref} {format_number(diff_fm_ref)}{val_suffix_html}</div>
                                <div class="sintesi-pct-det">{sign_fm_ref} {pct_fm_str}%</div>
                                <div style="font-size:18px; font-weight:normal; margin-top:5px; opacity:0.9;">Tot. {format_number(fm_prev_ref)}{sym}</div>
                            </div>
                            <div class="sintesi-box-detail {class_fa_ref}">
                                <div class="sintesi-val-det">{sign_fa_ref} {format_number(diff_fa_ref)}{val_suffix_html}</div>
                                <div class="sintesi-pct-det">{sign_fa_ref} {pct_fa_str}%</div>
                                <div style="font-size:18px; font-weight:normal; margin-top:5px; opacity:0.9;">Tot. {format_number(fa_prev_ref)}{sym}</div>
                            </div>
                        </div>
                    </div>'''
                
                else:
                    val_main_pct = 0.0
                    box_desc = "" 
                    desc_parts = []
                    
                    tot_ops = p_ops['Totali'].sum() if 'Totali' in p_ops else 1
                    tot_days = p_w['Totali'].sum() if 'Totali' in p_w else 1
                    tot_acts = df_ta['Totali'].sum() if 'Totali' in df_ta else 1
                    
                    if k_ref == '7': 
                        val_num = p_ops.loc['Marica', 'Totali'] if 'Marica' in p_ops.index else 0
                        val_main_pct = (val_num / tot_ops * 100) if tot_ops > 0 else 0
                        box_desc = "Percentuale di persone che storicamente scelgono il pomeriggio/sera"
                        # Struttura per PDF (Bold su pomeriggio/sera)
                        desc_parts = [
                            [{"t": "Percentuale di persone che", "b": 0}],
                            [{"t": "storicamente scelgono il", "b": 0}],
                            [{"t": "pomeriggio/sera", "b": 1}]
                        ]
                    
                    elif k_ref == '8': 
                        val_num = p_w.loc['Lun', 'Totali'] if 'Lun' in p_w.index else 0
                        val_main_pct = (val_num / tot_days * 100) if tot_days > 0 else 0
                        box_desc = "Percentuale di persone che storicamente scelgono il lunedì"
                        desc_parts = [
                            [{"t": "Percentuale di persone che", "b": 0}],
                            [{"t": "storicamente scelgono il", "b": 0}],
                            [{"t": "lunedì", "b": 1}]
                        ]
                        
                    elif k_ref == '9': 
                        idx_match = [i for i in df_ta.index if "FITNESS" in str(i).upper() or "SALA" in str(i).upper()]
                        val_num = 0
                        if idx_match: val_num = df_ta.loc[idx_match[0], 'Totali']
                        val_main_pct = (val_num / tot_acts * 100) if tot_acts > 0 else 0
                        box_desc = "Percentuale di persone che storicamente scelgono il Fitness"
                        desc_parts = [
                            [{"t": "Percentuale di persone che", "b": 0}],
                            [{"t": "storicamente scelgono il", "b": 0}],
                            [{"t": "Fitness", "b": 1}]
                        ]
                        
                    elif k_ref == '10': 
                        # MODIFICATO PER TOP 100: Denominatore corretto (Totale solo dell'anno corrente 'ac')
                        val_num = df_tc['Totali'].head(100).sum()
                        tot_gen_ac = df.loc[df['AnnoSportivo'] == ac, 'Totale'].sum()
                        val_main_pct = (val_num / tot_gen_ac * 100) if tot_gen_ac > 0 else 0
                        box_desc = "Quota di incassi generata dai Clienti Top 100 nell'anno in corso"
                        
                    elif k_ref == '11': 
                        val_num = df_lost_stats['Totali'].sum()
                        tot_ap = df.loc[df['AnnoSportivo']==ap, 'Totale'].sum()
                        val_main_pct = (val_num / tot_ap * 100) if tot_ap > 0 else 0
                        box_desc = "Percentuale di clienti dello scorso anno che stiamo aspettando"
                        
                    elif k_ref == '12': 
                        val_num = df_fedeli_stats['Totali'].sum()
                        tot_ap = df.loc[df['AnnoSportivo']==ap, 'Totale'].sum()
                        val_main_pct = (val_num / tot_ap * 100) if tot_ap > 0 else 0
                        box_desc = "Percentuale di clienti storici (dal 2021) che bisogna chiamare"

                    pct_str = f"{val_main_pct:.1f}".replace('.', ',')
                    
                    # SALVATAGGIO DATI PER PDF (Tipo Single)
                    clean_title = label_block.split('. ', 1)[1] if '. ' in label_block else label_block
                    
                    data_obj = {
                        "type": "single",
                        "title": clean_title, 
                        "pct": f"{pct_str}%",
                        "desc": box_desc,
                        "full_title": label_block
                    }
                    if desc_parts:
                        data_obj["desc_parts"] = desc_parts
                    
                    raw_sintesi_data.append(data_obj)
                    
                    content_block += f'''
                    <div style="margin-bottom:25px;">
                        <div class="sintesi-header-bar">{label_block}</div>
                        <div class="sintesi-grid">
                             <div class="sintesi-box-single" style="background-color: {COL_SINTESI_SINGLE_BG}; border-radius: 0 0 8px 8px; border: 1px solid #ccc; border-top: none;">
                                <div class="sintesi-val-single">{pct_str}%</div>
                                <div class="sintesi-desc-single">{box_desc}</div>
                             </div>
                        </div>
                    </div>'''

            content_block += '</div>'
        
        else:
            # --- FIX: RIPRISTINATA GENERAZIONE TABELLE DETTAGLIO ---
            is_temp = int(key) <= 6 
            is_curr = (key != '5') 
            is_graph_only = (int(key) in [7, 8, 9])
            suffix = " €" if is_curr else ""
            
            if key == '10': delta_html = f'<b style="color:#800000">Clienti:</b> {format_number(top_count)} <span style="margin-left:10px"></span> <b style="color:#800000">Tot:</b> {format_number(top_sum)} €'
            elif key == '11': delta_html = f'<b style="color:#800000">Clienti:</b> {format_number(lost_count)} <span style="margin-left:10px"></span> <b style="color:#800000">Tot:</b> {format_number(lost_sum)} €'
            elif key == '12': delta_html = f'<b style="color:#800000">Clienti:</b> {format_number(fedeli_count)} <span style="margin-left:10px"></span> <b style="color:#800000">Tot:</b> {format_number(fedeli_sum)} €'
            elif is_temp:
                 if key == '5': delta_html = f'<b style="color:#800000">Σ {ac}</b>: {format_number(cli_tot_ac)}'
                 elif key == '6': delta_html = f'<b style="color:#800000">µ {ac}</b>: {format_number(avg_tot_ac)}{suffix}'
                 else:
                     val_box = df_curr[ac].sum() if ac in df_curr.columns else 0
                     delta_html = f'<b style="color:#800000">Σ {ac}</b>: {format_number(val_box)}{suffix}'
            else:
                 val_box = df_curr['Totali'].sum() if 'Totali' in df_curr.columns else 0
                 delta_html = f'<b style="color:#800000">Σ Totale</b>: {format_number(val_box)}{suffix}'

            if is_graph_only:
                rows_html = "" 
                chart_html = generate_chart_html(df_curr, key, ap, ac, is_temporal=False, is_currency=is_curr, is_wide_label=True)
            else:
                rows_html = generate_rows_html(df_curr, key, ap, ac, dm, is_currency=is_curr)
                if key == '5':
                    df_c = pd.DataFrame(index=['X'], columns=[ap, ac, 'Previsioni'])
                    df_c.at['X', ap] = cli_tot_ap; df_c.at['X', ac] = cli_tot_ac; df_c.at['X', 'Previsioni'] = cli_tot_prev
                    chart_html = generate_chart_html(df_c, key, ap, ac, is_temporal=True, is_currency=False, is_wide_label=False)
                elif key == '6':
                    df_c = pd.DataFrame(index=['X'], columns=[ap, ac, 'Previsioni'])
                    df_c.at['X', ap] = avg_tot_ap; df_c.at['X', ac] = avg_tot_ac; df_c.at['X', 'Previsioni'] = avg_tot_prev
                    chart_html = generate_chart_html(df_c, key, ap, ac, is_temporal=True, is_currency=True, is_wide_label=False)
                elif key in ['10', '11', '12']:
                     chart_html = generate_chart_html(df_curr, key, ap, ac, is_temporal=False, is_currency=True, is_wide_label=True)
                else:
                    chart_html = generate_chart_html(df_curr, key, ap, ac, is_temporal=is_temp, is_currency=is_curr, is_wide_label=False)
            
            if key in ['10', '11', '12']: content_block = f"{chart_html}{rows_html}"
            else: content_block = f"{rows_html}{chart_html}"
            # --- FINE FIX ---

        if key == '0':
             text_html = f'''
             <div class="total-value" style="font-size:22px; display:flex; align-items:center; justify-content:center;">
                 <span class="flash-dot"></span>{DESCRIZIONI_TABELLE["0"]}
                 <span onclick="event.stopPropagation(); toggleAudio(\'{AUDIO_SINTESI_URL}\')" style="margin-left:5px; cursor:pointer;">📢</span>
             </div>'''
             
             # --- MODIFICA: Layout Sintesi [Home - Titolo - Stampante] ---
             desc_html = f'''
            <div class="total-row-container" onclick="copyToClipboard(this)" style="cursor:copy; position:relative; margin-bottom:15px;">
                <div class="nav-icon" onclick="goHome()">🏠</div>
                {text_html}
                <div class="nav-icon" onclick="handlePrintAction(0)">🖨️</div>
            </div>'''
             
             details_html += f'''
            <div id="tab_{idx}" class="detail-view">
                {desc_html}
                {content_block}
            </div>'''
        else:
            desc_html = f'<div class="desc-box">{desc_text}</div>' if desc_text else ""
            
            # --- MODIFICA: Layout Dettaglio [Home - Dati - Stampante] ---
            details_html += f'''
            <div id="tab_{idx}" class="detail-view">
                <div class="total-row-container">
                    <div class="nav-icon" onclick="goHome()">🏠</div>
                    <div class="total-value">{delta_html}</div>
                    <div class="nav-icon" onclick="handlePrintAction({idx})">🖨️</div>
                </div>
                {desc_html}
                {content_block}
                <div class="info-footer">{title}</div>
            </div>'''
        
    menu_html += '</div>'
    json_str = json.dumps(json_data)
    
    # Serializzazione dati JS
    sintesi_data_json = json.dumps(raw_sintesi_data)
    
    full_html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Analisi Dati">
    <link rel="apple-touch-icon" href="{IMG_ICON_URL}">
    <link rel="icon" type="image/jpeg" href="{IMG_ICON_URL}">
    <title>Analisi Dati</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
    body {{ font-family: 'Segoe UI', sans-serif; background-color: #f0f2f5; margin: 0; padding: 0; touch-action: pan-y; }}
    .main-container {{ background-color: white; margin: 0 auto; width: 100%; max-width: 490px; min-height: 100vh; box-shadow: 0 0 20px rgba(0,0,0,0.1); position: relative; padding-bottom: 20px; }}
    .header-box {{ background-color: {COL_BG_HEADER}; color: white; padding: 20px 15px; text-align: center; position: sticky; top: 0; z-index: 100; cursor: pointer; }}
    
    /* MODIFICA: Font ridotto titolo */
    #header-title {{ margin: 0; font-size: 24px; font-weight: 800; text-transform: uppercase; }}
    #header-subtitle {{ margin-top: 5px; font-size: 16px; opacity: 0.9; }}
    
    /* Layout header con frecce */
    .header-nav-container {{ display: flex; justify-content: space-between; align-items: center; width: 100%; }}
    .nav-arrow-header {{ font-size: 28px; cursor: pointer; padding: 0 10px; user-select: none; }}
    .header-center {{ flex-grow: 1; }}

    #menu-view {{ padding-bottom: 40px; padding-top: 20px; }}
    .menu-item {{ padding: 3px 20px; height: 50px; border-bottom: none; font-size: 34px; font-weight: 500; color: #333; cursor: pointer; display: flex; justify-content: space-between; align-items: center; line-height: 1; }}
    .menu-item:nth-child(odd) {{ background-color: #ffffff; }}
    .menu-item:nth-child(even) {{ background-color: #f8f9fa; }}
    .menu-item:hover, .menu-item.selected {{ background-color: #e2e6ea !important; }}
    .menu-item::after {{ content: '›'; font-size: 40px; color: #ccc; }}
    #menu-item-0::after {{ content: ''; display: none; }}
    
    .sintesi-header-bar {{ background-color: {COL_BARRA_RIEPILOGO}; color: white; text-align: center; font-size: 20px; font-weight: 700; padding: 8px 0; border-radius: 6px 6px 0 0; letter-spacing: 1px; text-transform: uppercase; }}
    .sintesi-grid {{ display: flex; flex-direction: row; border: 1px solid #ccc; border-top: none; border-radius: 0 0 6px 6px; overflow: hidden; }}
    
    .sintesi-box-detail {{ flex: 1; padding: 20px 10px; text-align: center; display: flex; flex-direction: column; justify-content: center; }}
    .sintesi-box-detail:first-child {{ border-right: 1px solid #eee; }}
    .sintesi-box-detail:last-child {{ border: 5px solid {COL_GOLD}; margin: -1px; z-index: 1; position: relative; }} 
    
    .sintesi-box-single {{ width: 100%; padding: 30px 15px; text-align: center; background-color: #fff; }}
    .sintesi-val-single {{ font-size: 56px; font-weight: 800; color: #333; margin-bottom: 10px; line-height: 1; }}
    .sintesi-desc-single {{ font-size: 18px; color: #666; font-weight: 500; padding: 0 20px; line-height: 1.4; }}

    .sintesi-box-detail.green {{ background-color: {COL_SINTESI_GREEN_BG}; color: {COL_SINTESI_GREEN_TXT}; }}
    .sintesi-box-detail.red {{ background-color: {COL_SINTESI_RED_BG}; color: {COL_SINTESI_RED_TXT}; }}
    
    .sintesi-lbl-det {{ display: none; }}
    .sintesi-val-det {{ font-size: 42px; font-weight: 800; line-height: 1.1; margin-bottom: 5px; }}
    .sintesi-pct-det {{ font-size: 20px; font-weight: 600; opacity: 0.9; }}

    .detail-view {{ display: none; padding: 5px 10px; animation: fadeIn 0.3s; }}
    @keyframes fadeIn {{ from {{ opacity:0; transform: translateY(10px); }} to {{ opacity:1; transform: translateY(0); }} }}
    .header-row {{ display: flex; justify-content: space-between; background-color: #c0c4c9; padding: 8px 2px; font-size: 20px; font-weight: 700; color: #495057; border-radius: 4px; margin-bottom: 5px; align-items: flex-start; }}
    .header-row-11 {{ font-size: 20px !important; }}
    .euro-sub {{ font-size: 0.9em; font-weight: 400; margin-top: 0px; line-height: 1; display: inline-block; }} 
    .col-lbl {{ width: 13%; text-align: left; font-size: 26px; white-space: nowrap; overflow: hidden; font-weight:600; color: #555; padding-top:2px; }}
    .col-val {{ width: 29%; text-align: center; font-size: 26px; line-height: 1.1; }}
    .data-row-3col {{ display: flex; justify-content: space-between; padding: 0; border-bottom: none; align-items: stretch; font-size: 20px; }}
    .data-row-3col span {{ padding: 2px 2px; border-bottom: 1px solid {COL_BORDER_GREY}; display: flex; align-items: center; justify-content: center; font-weight: 400; }}
    .data-row-3col .col-lbl {{ justify-content: flex-start; font-weight: 500; }}
    .data-row-4col {{ display: flex; justify-content: space-between; padding: 0; border-bottom: none; align-items: stretch; font-size: 19px; }}
    .data-row-4col span {{ padding: 4px 2px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; }}
    .col-prog {{ width: 10%; justify-content: center; font-weight: 600; display: flex; align-items: center; }}
    .col-name {{ width: 50%; justify-content: center; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; flex-direction: column; align-items: center; }}
    .col-freq {{ width: 15%; justify-content: center; display: flex; flex-direction: column; align-items: center; }}
    .col-money {{ width: 25%; justify-content: center; font-weight: 600; text-align: right; padding-right: 5px; display: flex; flex-direction: column; align-items: center; }}
    .sort-arrow {{ font-size: 0.8em; color: #777; margin-top: 2px; }}
    .sort-active {{ color: #dc3545; font-size: 1.2em; }}
    .data-row-4col .col-name {{ justify-content: flex-start; padding-left: 5px; align-items: center; }}
    .data-row-4col .col-money {{ justify-content: flex-end; align-items: center; }}
    
    /* MODIFICA: Layout navigazione dettaglio (Home - Centro - Stampante) */
    .total-row-container {{ position: relative; display: flex; justify-content: space-between; align-items: center; background-color: #f0f8ff; border-radius: 10px; padding: 10px; margin-bottom: 5px; margin-top: 10px; border: 1px solid #999; }}
    .nav-icon {{ font-size: 24px; cursor: pointer; padding: 0 10px; user-select: none; }}
    .total-value {{ font-size: 24px; font-weight: 600; color: #000; text-align: center; flex-grow: 1; }}
    
    .desc-box {{ background-color: #ffffff; padding: 10px; margin: 5px 2px 15px 2px; border-radius: 8px; border: 1px solid #999; font-size: 15px; color: #555; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); line-height: 1.3; }}

    /* STILE PER IL CERCHIO VERDE LAMPEGGIANTE (VELOCE 0.5s) */
    .flash-dot {{
        width: 12px;
        height: 12px;
        background-color: #32CD32;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
        vertical-align: middle;
        animation: flashing 0.5s infinite alternate;
    }}
    @keyframes flashing {{
        from {{ opacity: 1; box-shadow: 0 0 5px #32CD32; }}
        to {{ opacity: 0.3; box-shadow: 0 0 1px #32CD32; }}
    }}

    /* CHART CSS REINSERITO */
    .chart-container {{ margin-top: 20px; padding: 15px 10px; background-color: #fafafa; border-radius: 8px; border: 1px solid #999; margin-bottom: 20px; }}
    .chart-title {{ text-align: center; font-weight: 700; font-size: 16px; margin-bottom: 15px; color: #666; text-transform: uppercase; }}
    .chart-row {{ display: flex; align-items: center; margin-bottom: 8px; font-size: 13px; width: 100%; }}
    .chart-lbl {{ width: 70px; text-align: right; padding-right: 8px; color: #555; font-weight: 500; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .chart-lbl-wide {{ width: 165px; text-align: right; padding-right: 8px; color: #555; font-weight: 500; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px; }}
    .chart-bar-area {{ flex-grow: 1; background-color: #e9ecef; height: 12px; border-radius: 6px; overflow: hidden; margin-right: 8px; }}
    .chart-bar {{ height: 100%; border-radius: 6px; }}
    .chart-val {{ width: 60px; text-align: left; font-weight: 400; color: #333; font-size: 12px; flex-shrink: 0; white-space: nowrap; }}
    
    .info-footer {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; text-align: center; font-size: 11px; color: #999; }}
    #ptr-indicator {{ position: fixed; top: -50px; left: 0; width: 100%; height: 50px; display: flex; justify-content: center; align-items: center; background-color: #f0f2f5; color: #666; font-weight: 600; z-index: 9999; transition: top 0.3s; }}
    
    /* TOAST STYLE */
    #toast {{
        visibility: hidden;
        min-width: 250px;
        margin-left: -125px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 2px;
        padding: 16px;
        position: fixed;
        z-index: 1000;
        left: 50%;
        bottom: 30px;
        font-size: 17px;
    }}
    #toast.show {{
        visibility: visible;
        -webkit-animation: fadein 0.5s, fadeout 0.5s 2.5s;
        animation: fadein 0.5s, fadeout 0.5s 2.5s;
    }}
    @keyframes fadein {{ from {{bottom: 0; opacity: 0;}} to {{bottom: 30px; opacity: 1;}} }}
    @keyframes fadeout {{ from {{bottom: 30px; opacity: 1;}} to {{bottom: 0; opacity: 0;}} }}
    </style>
    <script>
        const TABLE_DATA = {json_str};
        const PDF_DATA_10 = {pdf_data_10_json};
        const PDF_DATA_11 = {pdf_data_11_json};
        const PDF_DATA_12 = {pdf_data_12_json};
        
        const SINTESI_DATA = {sintesi_data_json};
        const CAL_CURR = {cal_data_curr_json};
        const CAL_PREV = {cal_data_prev_json};
        const TITLE_CURR = "{title_curr}";
        const TITLE_PREV = "{title_prev}";
        
        const HOME_TITLE = "ANALISI DATI";
        const HOME_SUBTITLE = "Aggiornato al: {last_update_str}";
        const COUNTER_NS = "{COUNTER_NS}";
        const COUNTER_BASE_URL = "{COUNTER_BASE_URL}";
        const FINAL_LINK_JS = '{FINAL_LINK_JS}';
        
        (function() {{
            try {{
                const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
                const isStandalone = window.matchMedia('(display-mode: standalone)').matches || (window.navigator.standalone === true);
                if (isMobile && isStandalone) {{
                    if (!sessionStorage.getItem('has_autorefresh')) {{
                        sessionStorage.setItem('has_autorefresh', 'true');
                        window.location.reload();
                    }}
                }}
            }} catch(e) {{ console.error("Refresh error", e); }}
        }})();

        // LOGICA AUDIO
        var myAudio = null;
        var myAudioUrl = "";

        function toggleAudio(url) {{
            // MODIFICA: Aggiornamento contatore Audio
            updateAudioCounter();

            if (myAudio && myAudioUrl !== url) {{
                myAudio.pause();
                myAudio.currentTime = 0;
                myAudio = null;
            }}

            if (!myAudio) {{
                myAudio = new Audio(url);
                myAudioUrl = url;
                myAudio.play();
                return;
            }}

            if (myAudio.paused) {{
                var newTime = myAudio.currentTime - 2;
                if(newTime < 0) newTime = 0;
                myAudio.currentTime = newTime;
                myAudio.play();
            }} else {{
                myAudio.pause();
            }}
        }}
        
        // COPY TO CLIPBOARD
        function copyToClipboard(element) {{
            if (element.classList.contains('total-row-container') && element.innerText.includes("I numeri che parlano")) {{
                 copySintesiAll();
                 return;
            }}
        }}
        
        function copySintesiAll() {{
            const container = document.getElementById('tab_0');
            if(!container) return;
            let textResult = "SINTESI - I NUMERI CHE PARLANO\\nAggiornato al: {last_update_str}\\n\\n";
            const sections = container.querySelectorAll('div[style*="margin-bottom:25px"]');
            sections.forEach(sec => {{
                const title = sec.querySelector('.sintesi-header-bar').innerText;
                textResult += "--- " + title + " ---\\n";
                const boxes = sec.querySelectorAll('.sintesi-box-detail');
                if(boxes.length === 2) {{
                    const valLeft = boxes[0].querySelector('.sintesi-val-det').innerText.replace(/\\n/g, ' ');
                    const pctLeft = boxes[0].querySelector('.sintesi-pct-det').innerText;
                    const totLeftDiv = boxes[0].querySelector('div[style*="font-size:18px"]');
                    const totLeft = totLeftDiv ? totLeftDiv.innerText : "";
                    textResult += `FINE MESE: ${{valLeft}} (${{pctLeft}}) | ${{totLeft}}\\n`;
                    const valRight = boxes[1].querySelector('.sintesi-val-det').innerText.replace(/\\n/g, ' ');
                    const pctRight = boxes[1].querySelector('.sintesi-pct-det').innerText;
                    const totRightDiv = boxes[1].querySelector('div[style*="font-size:18px"]');
                    const totRight = totRightDiv ? totRightDiv.innerText : "";
                    textResult += `FINE ANNO: ${{valRight}} (${{pctRight}}) | ${{totRight}}\\n`;
                }}
                const singleBox = sec.querySelector('.sintesi-box-single');
                if(singleBox) {{
                    const val = singleBox.querySelector('.sintesi-val-single').innerText;
                    const desc = singleBox.querySelector('.sintesi-desc-single').innerText;
                    textResult += `${{val}} - ${{desc}}\\n`;
                }}
                textResult += "\\n";
            }});
            navigator.clipboard.writeText(textResult).then(() => {{ showToast(); }}).catch(err => console.error(err));
        }}

        function showToast() {{
            var x = document.getElementById("toast");
            x.className = "show";
            setTimeout(function(){{ x.className = x.className.replace("show", ""); }}, 2000);
        }}
        
        // --- LOGICA CONTATORI ---
        function checkAdmin() {{
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('admin')) {{
                localStorage.setItem('is_admin', '1');
                alert("Modalità ADMIN attivata. I contatori non verranno incrementati su questo dispositivo.");
            }}
             if (localStorage.getItem('is_admin') === '1') {{
                const sub = document.getElementById('header-subtitle');
                sub.style.color = "#ffdd00"; // Giallo
                sub.style.fontWeight = "800"; // Extra Bold
                sub.style.fontSize = "20px";  // Larger
            }}
        }}
        
        function updateCounter(tabIndex) {{
            if (localStorage.getItem('is_admin') === '1') {{ return; }}
            const key = "tab_" + tabIndex;
            const url = `${{COUNTER_BASE_URL}}/hit/${{COUNTER_NS}}_${{key}}`;
            fetch(url).catch(err => console.error("Counter error:", err));
        }}
        
        function updateAudioCounter() {{
            if (localStorage.getItem('is_admin') === '1') {{ return; }}
            // Key fissa per l'audio
            const url = `${{COUNTER_BASE_URL}}/hit/${{COUNTER_NS}}_audio_sintesi`;
            fetch(url).catch(err => console.error("Audio Counter error:", err));
        }}
        // ------------------------

        let currIdx = -1; 
        let menuIdx = 0; 
        const totalItems = {len(lista_chiavi)};

        function sortTable(wrapperId, criteria) {{
            const container = document.getElementById(wrapperId);
            if(!container) return;
            const header = container.previousElementSibling;
            header.querySelectorAll('.sort-arrow').forEach(a => {{ a.classList.remove('sort-active'); a.style.color="#777"; }});
            const activeArrow = header.querySelector('#sort-arrow-' + criteria);
            if(activeArrow) {{ activeArrow.classList.add('sort-active'); activeArrow.style.color="#dc3545"; }}

            const rows = Array.from(container.getElementsByClassName('data-row-4col'));
            rows.sort((a, b) => {{
                if(criteria === 'name') {{ const nA = a.getAttribute('data-name').toLowerCase(); const nB = b.getAttribute('data-name').toLowerCase(); return nA.localeCompare(nB); }} 
                else if(criteria === 'volte') {{ return parseFloat(b.getAttribute('data-volte')) - parseFloat(a.getAttribute('data-volte')); }} 
                else if(criteria === 'amount') {{ return parseFloat(b.getAttribute('data-amount')) - parseFloat(a.getAttribute('data-amount')); }}
            }});
            let c = 1;
            rows.forEach(row => {{ row.querySelector('.col-prog').innerText = c++; container.appendChild(row); }});
        }}

        function handleHeaderClick() {{
            // MODIFICATO: L'header principale gestisce SOLO la navigazione visiva se cliccato al centro (opzionale), ma le frecce sono separate.
            // Le azioni PDF sono ora delegate alla stampante.
        }}
        
        // --- FUNZIONE SPECIFICA PER IL TASTO STAMPANTE ---
        function handlePrintAction(idx) {{
            if (idx === 0) {{
                generateSintesiPDF();
                return;
            }}
            
            if(idx === 9) generateCompactPDF(10, "10. TOP 100 CLIENTI", PDF_DATA_10, {top_count}, 0, "{format_number(top_sum)}");
            else if(idx === 10) generateCompactPDF(11, "11. CLIENTI ATTESI", PDF_DATA_11, {lost_count}, {movimenti_persi}, "{format_number(lost_sum)}");
            else if(idx === 11) generateCompactPDF(12, "12. CLIENTI DA CHIAMARE", PDF_DATA_12, {fedeli_count}, 0, "{format_number(fedeli_sum)}");
            else window.location.href = FINAL_LINK_JS;
        }}
        
        // --- FUNZIONI NAVIGAZIONE AGGIUNTE ---
        function navPrev(e) {{
            e.stopPropagation();
            if(currIdx === -1) loadTable(totalItems - 1); // Da Home all'ultimo
            else if(currIdx === 0) goHome(); // Da Tab 0 a Home
            else loadTable(currIdx - 1); // Tab precedente
        }}
        
        function navNext(e) {{
            e.stopPropagation();
            if(currIdx === -1) loadTable(0); // Da Home a Tab 0
            else if(currIdx === totalItems - 1) goHome(); // Dall'ultimo a Home
            else loadTable(currIdx + 1); // Tab successiva
        }}
        
        // --- FUNZIONE NUOVA GENERAZIONE PDF SINTESI ---
        function generateSintesiPDF() {{
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF();
            const d = new Date();
            const dateStr = "{last_update_str}";
            
            // Header
            doc.setFontSize(16);
            doc.setFont("helvetica", "bold");
            doc.text("I NUMERI CHE PARLANO", 105, 15, {{align: "center"}});
            doc.setFontSize(10);
            doc.setFont("helvetica", "normal");
            doc.text(`Aggiornato al: ${{dateStr}}`, 105, 20, {{align: "center"}});
            
            let startY = 30;
            let colWidth = 90;
            let rowHeight = 35; 
            let marginX = 12;
            let gutter = 5; 
            let marginY = 5; 
            
            // --- GRIGLIA SUPERIORE (1-6) ---
            for(let i=0; i<6; i++) {{
                let item = SINTESI_DATA[i];
                let col = i % 2;
                let row = Math.floor(i / 2);
                let x = marginX + (col * (colWidth + gutter));
                let y = startY + (row * (rowHeight + marginY));
                
                // 1. Disegna sfondo giallo chiaro per la metà destra
                doc.setFillColor(255, 255, 240); // Giallo molto tenue (Ivory)
                doc.rect(x + colWidth/2, y + 7, colWidth/2, rowHeight - 7, 'F');
                
                // 2. Disegna Header Box
                doc.setFillColor(242, 242, 242); // Grigio chiarissimo
                doc.rect(x, y, colWidth, 7, 'F');
                
                // 3. Cornice Grigia Completa (sopra tutto)
                doc.setDrawColor(150, 150, 150);
                doc.setLineWidth(0.3);
                doc.rect(x, y, colWidth, rowHeight);
                
                // HEADER BORDER (Cornice specifica per il titolo)
                doc.rect(x, y, colWidth, 7); 

                // Testo Titolo (Normale, non grassetto)
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(9);
                doc.setFont("helvetica", "normal");
                doc.text(item.title, x + colWidth/2, y + 5, {{align: "center"}});
                
                // Linea Divisoria Centrale
                doc.setDrawColor(200, 200, 200);
                doc.line(x + colWidth/2, y + 7, x + colWidth/2, y + rowHeight);
                
                // Sinistra (Valore Principale)
                doc.setFontSize(20); 
                doc.setFont("helvetica", "bold");
                
                // COLOR LOGIC P1
                if (item.v1.includes("+")) doc.setTextColor(0, 100, 0); // Verde Scuro
                else if (item.v1.includes("-")) doc.setTextColor(139, 0, 0); // Rosso Scuro
                else doc.setTextColor(0, 0, 0);
                
                doc.text(item.v1, x + colWidth/4, y + 17, {{align: "center"}});
                
                // Sinistra (Percentuale)
                doc.setFontSize(9);
                doc.setFont("helvetica", "normal");
                
                if (item.p1.includes("+")) doc.setTextColor(0, 100, 0);
                else if (item.p1.includes("-")) doc.setTextColor(139, 0, 0);
                else doc.setTextColor(0, 0, 0);
                
                doc.text(item.p1, x + colWidth/4, y + 23, {{align: "center"}});
                
                doc.setFontSize(8);
                doc.setTextColor(80, 80, 80);
                doc.text(item.t1, x + colWidth/4, y + 29, {{align: "center"}});
                
                // Destra (Valore Principale)
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(20);
                doc.setFont("helvetica", "bold");
                
                if (item.v2.includes("+")) doc.setTextColor(0, 100, 0);
                else if (item.v2.includes("-")) doc.setTextColor(139, 0, 0);
                else doc.setTextColor(0, 0, 0);
                
                doc.text(item.v2, x + 3*colWidth/4, y + 17, {{align: "center"}});
                
                // Destra (Percentuale)
                doc.setFontSize(9);
                doc.setFont("helvetica", "normal");
                
                if (item.p2.includes("+")) doc.setTextColor(0, 100, 0);
                else if (item.p2.includes("-")) doc.setTextColor(139, 0, 0);
                else doc.setTextColor(0, 0, 0);
                
                doc.text(item.p2, x + 3*colWidth/4, y + 23, {{align: "center"}});
                
                doc.setFontSize(8);
                doc.setTextColor(80, 80, 80);
                doc.text(item.t2, x + 3*colWidth/4, y + 29, {{align: "center"}});
            }}

            // --- SEZIONE INFERIORE ---
            let startY_Bottom = startY + (3 * (rowHeight + marginY)) + 5; // Spazio Extra
            let leftGridY = startY_Bottom; 
            
            // 1) SINISTRA: BOX 7-12
            let subColW = (colWidth - gutter) / 2;
            let subRowH = rowHeight;
            
            for(let j=0; j<6; j++) {{
                let item = SINTESI_DATA[j+6];
                let sCol = j % 2; 
                let sRow = Math.floor(j / 2);
                
                let sx = marginX + (sCol * (subColW + gutter));
                let sy = leftGridY + (sRow * (subRowH + marginY));
                
                // Header (Grigio Chiaro)
                doc.setFillColor(242, 242, 242);
                doc.rect(sx, sy, subColW, 7, 'F');
                
                // Frame
                doc.setDrawColor(150, 150, 150);
                doc.setLineWidth(0.3);
                doc.rect(sx, sy, subColW, subRowH);
                
                // Header Border
                doc.rect(sx, sy, subColW, 7);
                
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(8); 
                doc.setFont("helvetica", "normal"); // Normale
                doc.text(item.title, sx + subColW/2, sy + 5, {{align: "center"}});
                
                // Contenuto (PCT)
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(16);
                doc.setFont("helvetica", "bold");
                doc.text(item.pct, sx + subColW/2, sy + 17, {{align: "center"}});
                
                // Contenuto (Descrizione)
                doc.setFontSize(7);
                doc.setTextColor(80, 80, 80);
                let descY = sy + 23;
                
                if (item.desc_parts) {{
                    // Rendering multilinea personalizzato con grassetto
                    item.desc_parts.forEach(lineArr => {{
                        let totalW = 0;
                        // Calcola larghezza totale riga per centrare
                        lineArr.forEach(part => {{
                            doc.setFont("helvetica", part.b ? "bold" : "normal");
                            totalW += doc.getTextWidth(part.t);
                        }});
                        
                        let currentX = sx + subColW/2 - totalW/2;
                        lineArr.forEach(part => {{
                            doc.setFont("helvetica", part.b ? "bold" : "normal");
                            doc.text(part.t, currentX, descY);
                            currentX += doc.getTextWidth(part.t) + 1; // +1 spacing
                        }});
                        descY += 3; // Interlinea
                    }});
                }} else {{
                    // Standard
                    doc.setFont("helvetica", "normal");
                    let splitDesc = doc.splitTextToSize(item.desc, subColW - 4);
                    doc.text(splitDesc, sx + subColW/2, descY, {{align: "center"}});
                }}
            }}

            // 2) DESTRA: CALENDARI
            let rightX = marginX + colWidth + gutter;
            let rightY = startY_Bottom;
            let totalCalHeight = (3 * subRowH) + (2 * marginY);
            let calColW = (colWidth - gutter) / 2;
            
            function drawCalendar(xPos, yPos, width, height, title, dataObj) {{
                // Header
                doc.setFillColor(242, 242, 242);
                doc.rect(xPos, yPos, width, 7, 'F');
                
                // Frame Esterno
                doc.setDrawColor(150, 150, 150);
                doc.setLineWidth(0.3);
                doc.rect(xPos, yPos, width, height);
                
                // Header Border
                doc.rect(xPos, yPos, width, 7);
                
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(8);
                doc.setFont("helvetica", "normal"); // Normale
                doc.text(title, xPos + width/2, yPos + 5, {{align: "center"}});
                
                // Dati
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(8); 
                doc.setFont("courier", "normal"); 
                
                let yLine = yPos + 11;
                let step = 3.5;
                
                dataObj.rows.forEach(row => {{
                    if (row.gap) {{
                        doc.setDrawColor(200, 200, 200);
                        doc.setLineWidth(0.1);
                        doc.line(xPos + 2, yLine - 2.5, xPos + width - 2, yLine - 2.5);
                    }}
                    
                    let dateStr = row.wday + " " + row.day.toString().padStart(2, '0');
                    doc.text(dateStr, xPos + 4, yLine);
                    
                    if(row.val && row.val !== "") {{
                         doc.text(row.val, xPos + width - 4, yLine, {{align: "right"}});
                    }}
                    
                    yLine += step;
                }});
                
                // Totale
                doc.setFont("helvetica", "bold");
                doc.setFontSize(9);
                doc.text("TOT: " + dataObj.total, xPos + width/2, yPos + height - 3, {{align: "center"}});
            }}
            
            drawCalendar(rightX, rightY, calColW, totalCalHeight, TITLE_PREV, CAL_PREV);
            drawCalendar(rightX + calColW + gutter, rightY, calColW, totalCalHeight, TITLE_CURR, CAL_CURR);

            doc.save("Sintesi.pdf");
            
            updateCounter(0);
        }}
        
        function generateCompactPDF(tabNum, pdfTitle, dataSet, statCount, statMov, statEuro) {{
             const {{ jsPDF }} = window.jspdf;
             const doc = new jsPDF();
             const d = new Date();
             const pad = (n) => n.toString().padStart(2, '0');
             const dateStr = "{last_update_str}";
             const fileName = `${{pdfTitle}}-${{d.getFullYear()}}-${{pad(d.getMonth()+1)}}-${{pad(d.getDate())}}.pdf`;
             
             doc.setFontSize(14); 
             doc.text(`${{pdfTitle}} (${{dateStr}})`, 105, 10, {{align: "center"}});
             doc.setFontSize(10);
             let sub = `(${{statCount}} clienti, ${{statEuro}} € totale)`;
             if(statMov > 0) sub = `(${{statCount}} clienti, ${{statMov}} movimenti, ${{statEuro}} € totale)`;
             doc.text(sub, 105, 16, {{align: "center"}});
             
             doc.setFontSize(9);
             const container = document.getElementById('list-wrapper-' + tabNum);
             const rows = Array.from(container.getElementsByClassName('data-row-4col'));
             let xStart = 10; let yStart = 25; 
             let colWidth = 65; 
             let pageHeight = 290; 
             let marginBot = 10;
             let x = xStart; let y = yStart; 
             let lineHeight = 5; 
             let count = 1;
             let itemsInGroup = 0;
             
             rows.forEach(row => {{
                 let name = row.getAttribute('data-name');
                 let volte = row.getAttribute('data-volte');
                 let amount = Math.round(parseFloat(row.getAttribute('data-amount')));
                 let amountStr = amount.toLocaleString('it-IT') + " €";
                 let txt = count + ") " + name.substring(0, 22) + " (" + volte + ") [" + amountStr + "]";
                 doc.text(txt, x, y);
                 y += lineHeight; count++; itemsInGroup++;
                 if (itemsInGroup >= 10) {{
                     doc.setDrawColor(180, 180, 180); doc.setLineWidth(0.1);
                     doc.line(x, y - 1, x + colWidth - 5, y - 1);
                     y += 2; itemsInGroup = 0;
                 }}
                 if (y > pageHeight - marginBot) {{
                     y = yStart; x += colWidth;
                     if (x > 200) {{ doc.addPage(); x = xStart; y = yStart; }}
                 }}
             }});
             doc.save(fileName);
             setTimeout(() => {{ window.open(doc.output('bloburl'), '_blank'); }}, 500);
        }}

        function updateMenuFocus() {{ for(let i=0; i<totalItems; i++) {{ let el = document.getElementById('menu-item-'+i); if(el) el.classList.remove('selected'); }} let cur = document.getElementById('menu-item-'+menuIdx); if(cur) {{ cur.classList.add('selected'); cur.scrollIntoView({{block: 'nearest'}}); }} }}
        
        function loadTable(index) {{ 
            currIdx = index; 
            menuIdx = index; 
            const data = TABLE_DATA[index]; 
            document.getElementById('header-title').innerText = data.title; 
            document.getElementById('header-subtitle').innerText = data.date; 
            document.getElementById('menu-view').style.display = 'none'; 
            const details = document.getElementsByClassName('detail-view'); 
            for(let d of details) d.style.display = 'none'; 
            const target = document.getElementById(data.id); 
            if(target) {{ target.style.display = 'block'; window.scrollTo(0,0); }} 
            
            // Incrementa contatore
            updateCounter(index);
        }}
        
        function goHome() {{ currIdx = -1; menuIdx = 0; const details = document.getElementsByClassName('detail-view'); for(let d of details) d.style.display = 'none'; document.getElementById('header-title').innerText = HOME_TITLE; document.getElementById('header-subtitle').innerText = HOME_SUBTITLE; document.getElementById('menu-view').style.display = 'block'; window.scrollTo(0,0); updateMenuFocus(); }}
        
        document.addEventListener('keydown', e => {{ if (currIdx === -1) {{ if(e.key === "ArrowDown") {{ menuIdx = (menuIdx + 1) % totalItems; updateMenuFocus(); e.preventDefault(); }} if(e.key === "ArrowUp") {{ menuIdx = (menuIdx - 1 + totalItems) % totalItems; updateMenuFocus(); e.preventDefault(); }} if(e.key === "Enter" || e.key === "ArrowRight") {{ loadTable(menuIdx); }} if(e.key === "ArrowLeft") {{ loadTable(totalItems - 1); }} }} else {{ if(e.key === "ArrowRight") {{ if (currIdx === TABLE_DATA.length - 1) goHome(); else loadTable(currIdx + 1); }} if(e.key === "ArrowLeft") {{ if (currIdx === 0) goHome(); else loadTable(currIdx - 1); }} if(e.key === "Backspace") goHome(); }} }});
        let touchStartX = 0; let touchEndX = 0; let pStart = {{x: 0, y:0}}; let pCurrent = {{x: 0, y:0}}; const ptr = document.getElementById('ptr-indicator');
        document.addEventListener('touchstart', e => {{ touchStartX = e.changedTouches[0].screenX; pStart.x = e.touches[0].screenX; pStart.y = e.touches[0].screenY; }}, {{passive: false}});
        document.addEventListener('touchmove', e => {{ pCurrent.x = e.touches[0].screenX; pCurrent.y = e.touches[0].screenY; const changeY = pCurrent.y - pStart.y; if (window.scrollY === 0 && changeY > 0 && currIdx === -1) {{ if (changeY > 60) {{ ptr.style.top = "0px"; ptr.innerText = "⬇️ Rilascia per aggiornare..."; }} }} }}, {{passive: false}});
        document.addEventListener('touchend', e => {{ touchEndX = e.changedTouches[0].screenX; const dist = touchEndX - touchStartX; const changeY = pCurrent.y - pStart.y; if (Math.abs(dist) > 50 && Math.abs(changeY) < 50) {{ if (currIdx === -1) {{ if (dist < 0) loadTable(menuIdx); if (dist > 0) loadTable(totalItems-1); }} else {{ if (dist < 0) {{ if(currIdx < TABLE_DATA.length - 1) loadTable(currIdx + 1); else goHome(); }} if (dist > 0) {{ if(currIdx === 0) goHome(); else loadTable(currIdx - 1); }} }} }} if (window.scrollY === 0 && changeY > 80 && currIdx === -1) {{ location.reload(true); }} else {{ ptr.style.top = "-50px"; }} }});
        
        // INIT
        window.onload = function() {{ 
            checkAdmin();
            updateMenuFocus(); 
        }};
    </script>
</head>
<body>
    <div id="toast">Copiato!</div>
    <div id="ptr-indicator">⬇️ Trascina giù per aggiornare</div>
    <div class="main-container">
        <div class="header-box" onclick="handleHeaderClick()">
            <div class="header-nav-container">
                <div class="nav-arrow-header" onclick="navPrev(event)">◀️</div>
                <div class="header-center">
                    <div id="header-title">ANALISI DATI</div>
                    <div id="header-subtitle">Aggiornato al: {last_update_str}</div>
                </div>
                <div class="nav-arrow-header" onclick="navNext(event)">▶️</div>
            </div>
        </div>
        {menu_html}
        {details_html}
    </div>
</body>
</html>"""

    with open(FILE_HTML_OUT, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"✅ Report creato: {FILE_HTML_OUT}")
    os.system(f"start {FILE_HTML_OUT}")

if __name__ == "__main__":
    genera_app()