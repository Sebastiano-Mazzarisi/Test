import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT

# --- CONFIGURAZIONE PAGINA (Mobile Friendly) ---
st.set_page_config(page_title="JF Report", page_icon="🖨️", layout="centered")

# --- CSS PERSONALIZZATO PER MOBILE ---
# Questo blocco ingrandisce i font e i bottoni per schermi touch
st.markdown("""
<style>
    /* Ingrandisce il testo delle etichette (Label) */
    .stMarkdown label, .stSelectbox label, .stDateInput label, .stTextInput label, .stRadio label {
        font-size: 1.2rem !important;
        font-weight: bold;
    }
    /* Ingrandisce il testo dentro gli input */
    .stTextInput input {
        font-size: 1.1rem !important;
    }
    /* Rende il bottone Download Enorme e facile da premere */
    div.stDownloadButton > button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.5rem !important;
        font-weight: bold;
        background-color: #FF4B4B;
        color: white;
        border-radius: 10px;
    }
    div.stButton > button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.3rem !important;
        font-weight: bold;
        border-radius: 10px;
    }
    /* Spaziatura più ariosa */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAZIONE LOGICA ---
LIGHT_GRAY = colors.Color(0.90, 0.90, 0.90) 

# ==========================================
# FUNZIONI DI UTILITÀ
# ==========================================

def get_italian_date_string(dt):
    giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    mesi = ['', 'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 
            'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
    wd = giorni[dt.weekday()]
    return f"{wd} {dt.day} {mesi[dt.month]} {dt.year}"

def get_compact_date_string(dt):
    giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    return f"{giorni[dt.weekday()]} {dt.strftime('%d/%m/%Y')}"

def format_currency(val):
    if val == 0: return ""
    s = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if s.endswith(',00'): s = s[:-3]
    return f"{s} €"

def format_currency_total(val):
    s = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if s.endswith(',00'): s = s[:-3]
    return f"{s} €"

# ==========================================
# MOTORE GENERAZIONE PDF
# ==========================================

def generate_pdf_bytes(df, mode, date_args, sintetic_mode):
    buffer = io.BytesIO()
    
    try:
        if mode == 'SINGLE':
            target = pd.to_datetime(date_args[0])
            df = df[df['Data'] == target]
        elif mode == 'RANGE':
            start = pd.to_datetime(date_args[0])
            end = pd.to_datetime(date_args[1])
            df = df[(df['Data'] >= start) & (df['Data'] <= end)]
    except Exception as e:
        return None, f"Errore date: {e}"

    if df.empty:
        return None, "Nessun dato trovato."

    df = df.sort_values(['Data', 'Nominativo'])
    grouped = df.groupby('Data', sort=False)

    doc = BaseDocTemplate(buffer, pagesize=A4, 
                          rightMargin=5*mm, leftMargin=5*mm, 
                          topMargin=10*mm, bottomMargin=10*mm)
    
    elements = []
    grand_tot_c, grand_tot_p, grand_tot_u = 0, 0, 0
    giorni_stampati = 0

    if sintetic_mode:
        page_width, page_height = A4
        margin = 5*mm; gutter = 3*mm 
        col_width = (page_width - 2*margin - 2*gutter) / 3
        
        frames = [
            Frame(margin, margin, col_width, page_height - 2*margin, id='col1'),
            Frame(margin + col_width + gutter, margin, col_width, page_height - 2*margin, id='col2'),
            Frame(margin + 2*col_width + 2*gutter, margin, col_width, page_height - 2*margin, id='col3')
        ]
        doc.addPageTemplates([PageTemplate(id='ThreeCol', frames=frames)])
        col_widths = [col_width - 26*mm, 13*mm, 13*mm] 
    else:
        frame = Frame(10*mm, 10*mm, A4[0]-20*mm, A4[1]-20*mm, id='normal')
        doc.addPageTemplates([PageTemplate(id='OneCol', frames=[frame])])
        col_widths = [45*mm, 30*mm, 30*mm, 18*mm, 18*mm, 18*mm, 20*mm, 8*mm, 8*mm]

    for date, group in grouped:
        group = group.sort_values('Nominativo')
        income = group[group['Uscite'] == 0]
        expenses = group[group['Uscite'] > 0]
        
        tc = group['Contanti'].sum()
        tp = group['Pos'].sum()
        tu = group['Uscite'].sum()
        tot_inc = tc + tp
        
        if tot_inc == 0 and tu == 0: continue
        giorni_stampati += 1
        grand_tot_c += tc; grand_tot_p += tp; grand_tot_u += tu

        if sintetic_mode:
            h_txt = f"{get_compact_date_string(date)} - Totale: {format_currency_total(tot_inc)}"
            h_style = TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 8),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,0), (-1,-1), LIGHT_GRAY), ('PADDING', (0,0), (-1,-1), 2)
            ])
            elements.append(Table([[h_txt]], colWidths=[col_width], style=h_style))
            
            t_data = []
            for _, r in income.iterrows():
                t_data.append([r['Nominativo'], format_currency(r['Contanti']), format_currency(r['Pos'])])
            for _, r in expenses.iterrows():
                t_data.append([f"{r['Nominativo']} ({format_currency(r['Uscite'])})", "", ""])
            
            t = Table(t_data, colWidths=col_widths)
            ts = [('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 7),
                  ('ALIGN', (1,0), (2,-1), 'RIGHT'), ('GRID', (0,0), (-1,-1), 0.5, colors.black)]
            start_exp = len(income)
            for i in range(start_exp, len(t_data)):
                ts.append(('SPAN', (0,i), (-1,i)))
            t.setStyle(TableStyle(ts))
            elements.append(t)
            elements.append(Spacer(1, 3*mm))

        else: 
            h_txt = f"{get_italian_date_string(date)} - Totale {format_currency_total(tot_inc)}"
            elements.append(Table([[h_txt]], colWidths=[sum(col_widths)], style=TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,0), (-1,-1), LIGHT_GRAY)
            ])))
            
            t_data = [["Nominativo", "Attività", "Abbonamento", "Contanti", "Pos", "Uscite", "Operatore", "X", "Reg"]]
            for _, r in pd.concat([income, expenses]).iterrows():
                row = []
                for c in ['Nominativo', 'Attività', 'Abbonamento', 'Contanti', 'Pos', 'Uscite', 'Operatore', 'CassaX', 'Registrato']:
                    v = r.get(c, "")
                    if c in ['Contanti', 'Pos', 'Uscite']: v = format_currency(v)
                    row.append(str(v))
                t_data.append(row)
            t_data.append(["TOTALE", "", "", format_currency(tc), format_currency(tp), format_currency(tu), "", "", ""])
            
            t = Table(t_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.white), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
            ]))
            elements.append(t)
            elements.append(Spacer(1, 5*mm))

    if giorni_stampati > 0:
        elements.append(Spacer(1, 5*mm))
        s_style = ParagraphStyle('S', parent=getSampleStyleSheet()['Normal'], alignment=TA_RIGHT, fontSize=10)
        elements.append(Paragraph(f"TOTALE: {format_currency_total(grand_tot_c + grand_tot_p)}", s_style))
        elements.append(Paragraph(f"Contanti: {format_currency_total(grand_tot_c)}", s_style))
        elements.append(Paragraph(f"Pos: {format_currency_total(grand_tot_p)}", s_style))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(f"Uscite: {format_currency_total(grand_tot_u)}", s_style))
        
        try:
            doc.build(elements)
            buffer.seek(0)
            return buffer, "OK"
        except Exception as e:
            return None, str(e)
    return None, "Nessun dato."

# ==========================================
# INTERFACCIA WEB (STREAMLIT)
# ==========================================

st.title("🖨️ JF Report")

# 1. Caricamento Dati
try:
    df = pd.read_csv('JF-DB.csv')
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    
    cols_num = ['Contanti', 'Pos', 'Uscite']
    for c in cols_num:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace('.', '').str.replace(',', '.')
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    if 'Nominativo' not in df.columns: df['Nominativo'] = ""
    df['Nominativo'] = df['Nominativo'].astype(str).str.strip()
    
    df.loc[df['Nominativo'].str.lower() == 'marica', 'Nominativo'] = 'Pricci Marica'
    df.loc[df['Nominativo'].str.lower() == 'checco', 'Nominativo'] = 'Di Stasio Checco'

except FileNotFoundError:
    st.error("ERRORE CRITICO: File 'JF-DB.csv' non trovato sul server.")
    st.stop()

# 2. SEZIONE FILTRI (In un expander per pulizia su mobile)
with st.expander("📅 Impostazioni Ricerca (Clicca)", expanded=True):
    
    st.markdown("### Periodo")
    periodo_tutto = st.checkbox("Tutto il periodo", value=True)
    
    # Due colonne per le date, su mobile vanno una sotto l'altra
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Dal:", disabled=periodo_tutto)
    d2 = c2.date_input("Al:", disabled=periodo_tutto)

    st.markdown("---")
    st.markdown("### Formato")
    formato = st.radio("Scegli layout:", ["Sintetico (3 Colonne)", "Standard"], horizontal=True)
    is_sintetico = (formato == "Sintetico (3 Colonne)")

    st.markdown("---")
    st.markdown("### Filtri Nome")
    filter_inc = st.text_input("Solo chi contiene:", placeholder="es. giulia")
    filter_exc = st.text_input("Escludi chi contiene:", placeholder="es. rossi")

# 3. LOGICA APPLICAZIONE FILTRI
df_filtered = df.copy()

if filter_inc:
    for w in filter_inc.split():
        df_filtered = df_filtered[df_filtered['Nominativo'].str.contains(w, case=False, na=False)]
if filter_exc:
    for w in filter_exc.split():
        df_filtered = df_filtered[~df_filtered['Nominativo'].str.contains(w, case=False, na=False)]

mode = 'ALL'
date_args = []
if not periodo_tutto:
    if d1 == d2:
        mode = 'SINGLE'
        date_args = [d1]
    else:
        mode = 'RANGE'
        date_args = [d1, d2]

# 4. BOTTONE E GENERAZIONE
st.markdown("###") # Spazio vuoto

# Generazione in memoria
pdf_bytes, msg = generate_pdf_bytes(df_filtered, mode, date_args, is_sintetico)

if pdf_bytes:
    # Se il PDF è pronto, mostra il bottone per scaricarlo
    # Usiamo use_container_width=True per farlo largo quanto lo schermo
    st.download_button(
        label="⬇️ SCARICA IL REPORT PDF",
        data=pdf_bytes,
        file_name="JF-Stampa.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.success(f"Trovati dati per {len(df_filtered)} righe.")
else:
    # Se non ci sono dati o c'è errore
    st.error(msg)