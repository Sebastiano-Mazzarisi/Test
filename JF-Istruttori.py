# Nome script: JF-Istruttori.py
# Data: 02/01/2026
# Descrizione: Report istruttori con STATE-BASED SORTING (Fix definitivo ordinamento PDF).

import pandas as pd
import re
import sys
import json
import webbrowser
import os

FILE_INPUT = 'JF-DB.csv'
FILE_OUTPUT_HTML = 'Report_Istruttori.html'

# ================= DATA PROCESSING =================
def estrai_istruttore(row):
    att = str(row.get('Attività', '')).strip().lower()
    abb = str(row.get('Abbonamento', ''))
    if att == 'calisthenics': return "Calisthenics (Matteo)"
    if att == 'defensystem': return "Defensystem (Saverio)"
    if att == 'kravmaga': return "KravMaga (Saverio)"
    if att == 'ried.funz.': return "Ried.Funz. (Mimmo)"
    if att == 'personal':
        m = re.search(r'\((.*?)\)', abb)
        return f"Personal ({m.group(1).strip().title()})" if m else None
    return None

def pulisci_abbonamento(testo):
    return re.sub(r'(\S)\(', r'\1 (', str(testo))

def carica_dati():
    df = pd.read_csv(FILE_INPUT, sep=None, engine='python')
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['periodo'] = df['Data'].dt.strftime('%Y-%m')
    df['Istruttore'] = df.apply(estrai_istruttore, axis=1)
    for c in ['Contanti', 'Pos']:
        df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0).astype(int)
    return df[df['Istruttore'].notna()].copy()

def build_structure(df):
    out = {}
    for periodo, g in df.groupby('periodo'):
        out[periodo] = {"istruttori": {}}
        for istr, gi in g.groupby('Istruttore'):
            det = []
            tc = tp = 0
            for _, r in gi.sort_values('Data').iterrows():
                c, p = int(r['Contanti']), int(r['Pos'])
                tc += c; tp += p
                det.append({
                    "data": r['Data'].strftime('%d/%m/%Y'),
                    "day_val": int(r['Data'].day), # Per ordinamento numerico giorno
                    "attivita": str(r.get('Attività', '')),
                    "abbonamento": pulisci_abbonamento(r.get('Abbonamento', '')),
                    "contanti": c,
                    "pos": p,
                    "totale": c + p
                })
            out[periodo]["istruttori"][istr] = {
                "totale": tc + tp, "contanti": tc, "pos": tp, "dettagli": det
            }
    return out

# ================= HTML GENERATION =================
def genera_html(data, periodo_default, min_p, max_p):
    json_data = json.dumps(data, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Report Istruttori</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.29/jspdf.plugin.autotable.min.js"></script>
<style>
body {{ font-family: system-ui, sans-serif; background: #eef2f7; padding: 12px; }}
.card {{ max-width: 1100px; margin: auto; background: white; border-radius: 14px; box-shadow: 0 8px 20px rgba(0,0,0,.15); padding: 20px; display: flex; flex-direction: column; align-items: center; }}

#periodo {{ display: none; }}

.nav-table {{ margin-bottom: 20px; border-collapse: separate; border-spacing: 0; }}
.nav-table td {{ border: none; background: transparent; text-align: center; vertical-align: middle; padding: 5px; }}
.nav-arrow {{ font-size: 2rem; color: #3b82f6; cursor: pointer; user-select: none; font-weight: bold; transition: transform 0.1s; }}
.nav-arrow:hover {{ color: #2563eb; transform: scale(1.1); }}
.nav-arrow:active {{ transform: scale(0.9); }}

.nav-label {{ font-size: 1.5rem; font-weight: bold; color: #1e293b; text-transform: uppercase; min-width: 200px; cursor: pointer; user-select: none; }}
.nav-label:hover {{ color: #3b82f6; }}

#main, #detail {{ width: 100%; margin-bottom: 25px; }}

table {{ border-collapse: collapse; margin-top: 8px; }}
th, td {{ border: 1px solid #000; padding: 3px 6px; font-size: 0.95rem; line-height: 1.0; }}
th {{ background: #e5e7eb; }}

/* STILI ALTEZZA RADDOPPIATA NEL DETTAGLIO */
#detailTable thead tr.row-yellow td {{ padding-top: 12px; padding-bottom: 12px; font-size: 1.2rem; }}
#detailTable thead tr th {{ padding-top: 10px; padding-bottom: 10px; }}
#detailTable tfoot tr td {{ padding-top: 10px; padding-bottom: 10px; }}

th.sortable {{ cursor: pointer; position: relative; padding-right: 15px; user-select: none; }}
th.sortable:hover {{ background: #d1d5db; }}
th.sortable::after {{ content: '⇕'; position: absolute; right: 2px; opacity: 0.3; font-size: 0.8em; }}
th.sortable.asc::after {{ content: '▲'; opacity: 1; color: #000; }}
th.sortable.desc::after {{ content: '▼'; opacity: 1; color: #000; }}

tr.click {{ cursor: pointer; }}
tr.click:hover {{ background: #e0f2fe; }}
.row-yellow {{ font-weight: bold; background: #fef3c7; }}
.row-gray {{ font-weight: bold; background: #e5e7eb; }}
.note {{ color: #64748b; margin-top: 20px; text-align: center; }}
.num {{ text-align: right; }}

#main table tr td, #main table tr th {{ line-height: 1.8; }}

#nav-container table, #main table {{ width: 40%; margin: 0 auto; }}
#detail table {{ width: 55%; margin: 0 auto; }}

@media (max-width: 768px) {{
    #nav-container table, #main table {{ width: 96%; }}
    #detail table {{ width: 100%; }}
    .card {{ padding: 10px; }}
    th, td {{ font-size: 0.85rem; padding: 4px; }}
    .btns button {{ width: 100%; margin-bottom: 10px; margin-left: 0; }}
    .nav-label {{ font-size: 1.2rem; min-width: auto; }}
}}

.btns {{ display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-top: auto; padding-top: 10px; border-top: 1px solid #eee; width: 100%; }}
.btns button {{ padding: 8px 16px; font-size: 0.85rem; cursor: pointer; background: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
.btns button:hover {{ background: #2563eb; transform: translateY(-1px); }}
</style>
</head>
<body>
<div class="card">
  <input type="month" id="periodo" min="{min_p}" max="{max_p}">
  <div id="nav-container" style="width:100%">
    <table class="nav-table">
        <tr>
            <td style="width:15%"><div class="nav-arrow" onclick="changeMonth(-1)">&#10094;</div></td>
            <td style="width:70%"><div id="nav-label" class="nav-label" onclick="resetToMax()" title="Torna all'ultimo mese"></div></td>
            <td style="width:15%"><div class="nav-arrow" onclick="changeMonth(1)">&#10095;</div></td>
        </tr>
    </table>
  </div>
  <div id="main"></div>
  <div id="detail" style="display:none;"></div>
  <div class="btns">
      <button onclick="genPDF('sintetico')">PDF Sintetico</button>
      <button onclick="genPDF('completo')">PDF Completo</button>
  </div>
</div>

<script>
const {{ jsPDF }} = window.jspdf;
const DATA = {json_data};
const input = document.getElementById("periodo");
input.value = "{periodo_default}";
let currentInstructor = null;

// --- GESTIONE STATO ORDINAMENTO ---
// Variabili globali per memorizzare l'ultimo ordinamento richiesto
let homeSortState = {{ col: 0, dir: 'asc' }};
let detailSortState = {{ col: 0, dir: 'asc' }}; // Default per dettaglio (Col 0 = Giorno)

// --- CONTATORE VISITE ---
fetch("https://countapi.mileshilliard.com/api/v1/hit/joyfit-stats-v1_report_istruttori").catch(e=>console.log(e));

const euro = (v) => v ? "€ " + v.toString().replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ".") : "";
const MONTHS = ["", "GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"];

document.addEventListener('keydown', function(event) {{
    if (event.key === 'ArrowLeft') changeMonth(-1);
    else if (event.key === 'ArrowRight') changeMonth(1);
}});

function updateNavLabel() {{
    const val = input.value; 
    if(!val) return;
    const parts = val.split('-');
    document.getElementById('nav-label').innerText = `${{MONTHS[parseInt(parts[1], 10)]}} ${{parts[0]}}`;
}}

// QUANDO SI CAMBIA MESE: Reset completo
function onPeriodChange() {{
    updateNavLabel();
    // Reset ordinamenti ai default quando cambio mese
    homeSortState = {{ col: 0, dir: 'asc' }};
    detailSortState = {{ col: 0, dir: 'asc' }};
    renderHome();       
}}

function resetToMax() {{ input.value = input.max; onPeriodChange(); }}

function changeMonth(delta) {{
    const currentVal = input.value;
    const d = new Date(currentVal + "-01");
    d.setMonth(d.getMonth() + delta);
    const newVal = `${{d.getFullYear()}}-${{String(d.getMonth() + 1).padStart(2, '0')}}`;
    if (newVal < input.min || newVal > input.max) return;
    input.value = newVal;
    onPeriodChange();
}}

function getNiceTitle(isoDate) {{
    if (!isoDate) return "";
    const parts = isoDate.split('-');
    const m = parseInt(parts[1], 10);
    const monthsPdf = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];
    return `Report ${{monthsPdf[m]}} ${{parts[0]}}`;
}}

// Helper per parsing valori
function parseVal(val) {{
    if (!val) return -999999999;
    let s = val.toLowerCase().trim();
    if (s.includes('€') || /^[0-9.,]+$/.test(s)) {{
        let clean = s.replace(/[^0-9,-]/g, "");
        clean = clean.split('.').join('').replace(',', '.');
        let f = parseFloat(clean);
        return isNaN(f) ? -999999999 : f;
    }}
    return s;
}}

// Funzione di ordinamento visivo (DOM) + Aggiornamento Stato
function sortTable(tableId, n) {{
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById(tableId);
  switching = true;
  
  // Recupera lo stato attuale per decidere direzione iniziale
  let currentState = (tableId === 'homeTable') ? homeSortState : detailSortState;
  
  // Se clicco su una colonna diversa, parto sempre 'asc'. Se stessa, inverto.
  if (currentState.col === n) {{
      dir = (currentState.dir === 'asc') ? 'desc' : 'asc';
  }} else {{
      dir = 'asc';
  }}

  // AGGIORNA LE VARIABILI DI STATO GLOBALI
  if (tableId === 'homeTable') {{
      homeSortState = {{ col: n, dir: dir }};
  }} else {{
      detailSortState = {{ col: n, dir: dir }};
  }}
  
  // Aggiorna icone UI
  var headers = table.querySelectorAll("th.sortable");
  headers.forEach(h => h.classList.remove("asc", "desc"));
  headers[n].classList.add(dir);
  
  // Esegui ordinamento DOM (Bubble sort semplificato)
  while (switching) {{
    switching = false;
    rows = table.getElementsByTagName("tbody")[0].rows;
    for (i = 0; i < (rows.length - 1); i++) {{
      shouldSwitch = false;
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      let xVal = parseVal(x.innerText);
      let yVal = parseVal(y.innerText);
      if (dir == "asc") {{ if (xVal > yVal) {{ shouldSwitch = true; break; }} }}
      else if (dir == "desc") {{ if (xVal < yVal) {{ shouldSwitch = true; break; }} }}
    }}
    if (shouldSwitch) {{
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchcount ++;      
    }}
  }}
}}

// --- FUNZIONI ORDINAMENTO DATI (PER PDF) ---
// Queste funzioni ordinano i dati JSON in memoria basandosi sulle variabili di stato

function getSortedInstructors() {{
    const key = input.value;
    if (!DATA[key]) return [];
    let list = Object.keys(DATA[key].istruttori);
    
    // Ordina lista istruttori secondo homeSortState
    list.sort((a, b) => {{
        let valA, valB;
        if (homeSortState.col === 0) {{ // Nome
            valA = a.toLowerCase(); valB = b.toLowerCase();
        }} else {{ // Totale (col 1)
            valA = DATA[key].istruttori[a].totale;
            valB = DATA[key].istruttori[b].totale;
        }}
        
        if (valA < valB) return homeSortState.dir === 'asc' ? -1 : 1;
        if (valA > valB) return homeSortState.dir === 'asc' ? 1 : -1;
        return 0;
    }});
    return list;
}}

function getSortedDetails(nome) {{
    const key = input.value;
    // Clona array per non alterare l'originale
    let details = [...DATA[key].istruttori[nome].dettagli];
    
    details.sort((a, b) => {{
        let valA, valB;
        // Mapping colonna -> campo dati
        // 0: Giorno, 1: Abbonamento, 2: Cont, 3: POS, 4: Totale
        switch(detailSortState.col) {{
            case 0: valA = a.day_val; valB = b.day_val; break;
            case 1: valA = a.abbonamento.toLowerCase(); valB = b.abbonamento.toLowerCase(); break;
            case 2: valA = a.contanti; valB = b.contanti; break;
            case 3: valA = a.pos; valB = b.pos; break;
            case 4: valA = a.totale; valB = b.totale; break;
            default: valA = a.day_val; valB = b.day_val;
        }}
        
        if (valA < valB) return detailSortState.dir === 'asc' ? -1 : 1;
        if (valA > valB) return detailSortState.dir === 'asc' ? 1 : -1;
        return 0;
    }});
    return details;
}}

function renderHome() {{
  const key = input.value;
  const main = document.getElementById("main");
  document.getElementById("detail").innerHTML = ""; 
  document.getElementById("detail").style.display = 'none';
  main.style.display = 'block';
  currentInstructor = null;

  if (!DATA[key]) {{ main.innerHTML = "<div class='note'>Nessun dato.</div>"; return; }}

  // Recupera lista ordinata in base allo stato attuale (che è stato resettato o mantenuto)
  const sortedList = getSortedInstructors();
  let grandTotal = 0;

  // Header con classi per icona sort
  const th0Class = homeSortState.col === 0 ? `sortable ${{homeSortState.dir}}` : 'sortable';
  const th1Class = homeSortState.col === 1 ? `sortable ${{homeSortState.dir}}` : 'sortable';

  let h = `<table id="homeTable">
            <thead>
                <tr>
                    <th class="${{th0Class}}" onclick="sortTable('homeTable', 0)">Istruttore</th>
                    <th class="${{th1Class}} num" onclick="sortTable('homeTable', 1)">Totale Mese</th>
                </tr>
            </thead>
            <tbody>`;
  
  sortedList.forEach(nome => {{
    const t = DATA[key].istruttori[nome].totale;
    grandTotal += t;
    h += `<tr class="click" onclick="renderDetail('${{nome}}')"><td>${{nome}}</td><td class="num">${{euro(t)}}</td></tr>`;
  }});
  h += `</tbody><tfoot><tr class="row-gray"><td>TOTALE</td><td class="num">${{euro(grandTotal)}}</td></tr></tfoot></table>`;
  main.innerHTML = h;
}}

function renderDetail(nome) {{
  const key = input.value;
  currentInstructor = nome;
  const d = DATA[key].istruttori[nome];
  
  // Recupera dettagli ordinati secondo lo stato attuale
  const sortedDetails = getSortedDetails(nome);

  // Classi dinamiche per le intestazioni
  const getCls = (idx) => detailSortState.col === idx ? `sortable ${{detailSortState.dir}}` : 'sortable';

  let h = `<table id="detailTable">
      <thead>
          <tr class="row-yellow"><td colspan="5">${{nome}}</td></tr>
          <tr>
            <th class="${{getCls(0)}}" onclick="sortTable('detailTable', 0)">G</th>
            <th class="${{getCls(1)}}" onclick="sortTable('detailTable', 1)">Abbonamento</th>
            <th class="${{getCls(2)}} num" onclick="sortTable('detailTable', 2)">Cont.</th>
            <th class="${{getCls(3)}} num" onclick="sortTable('detailTable', 3)">POS</th>
            <th class="${{getCls(4)}} num" onclick="sortTable('detailTable', 4)">Totale</th>
          </tr>
      </thead>
      <tbody>`;

  sortedDetails.forEach(r => {{
    h += `<tr>
            <td style="text-align:center">${{parseInt(r.data.split('/')[0], 10)}}</td>
            <td>${{r.abbonamento.split('(')[0].trim()}}</td>
            <td class="num">${{euro(r.contanti)}}</td>
            <td class="num">${{euro(r.pos)}}</td>
            <td class="num">${{euro(r.totale)}}</td>
          </tr>`;
  }});

  h += `</tbody>
        <tfoot>
            <tr class="row-gray">
                <td colspan="2">TOTALE</td>
                <td class="num">${{euro(d.contanti)}}</td>
                <td class="num">${{euro(d.pos)}}</td>
                <td class="num">${{euro(d.totale)}}</td>
            </tr>
        </tfoot>
        </table>
      <div style="margin-top:10px; cursor:pointer; color:blue; text-align:center;" onclick="renderHome()">⬅ Torna all'elenco</div>`;

  const detailDiv = document.getElementById("detail");
  detailDiv.innerHTML = h;
  document.getElementById("main").style.display = 'none';
  detailDiv.style.display = 'block';
}}

function genPDF(mode) {{
  const key = input.value;
  if (!DATA[key]) return alert("Nessun dato.");
  
  const doc = new jsPDF('p', 'mm', 'a4');
  let y = 15;
  const TABLE_WIDTH = 150; 
  const LEFT_MARGIN = 30;  
  const FONT_SIZE = 11;    
  const styles = {{ fontSize: FONT_SIZE, cellPadding: 0.8, lineHeight: 1.0, valign: 'middle' }};
  const headStyles = {{ fillColor: [229, 231, 235], textColor: 0, fontStyle: 'bold', halign: 'center' }};
  const totalStyle = {{ fontStyle: 'bold', fillColor: [220, 220, 220] }};
  const numStyle = {{ halign: 'right' }};

  function checkPage(h) {{ if (y + h > 280) {{ doc.addPage(); y = 15; }} }}

  function addTable(nome) {{
    const d = DATA[key].istruttori[nome];
    // QUI STA LA MAGIA: Uso getSortedDetails che legge la variabile globale detailSortState
    const sourceData = getSortedDetails(nome); 
    
    const body = sourceData.map(r => [r.data, r.attivita, r.abbonamento, euro(r.contanti), euro(r.pos), euro(r.totale)]);
    body.push([{{ content:'TOTALE', colSpan:3, styles: totalStyle }}, {{ content:euro(d.contanti), styles: {{ ...totalStyle, halign:'right' }} }}, {{ content:euro(d.pos), styles: {{ ...totalStyle, halign:'right' }} }}, {{ content:euro(d.totale), styles: {{ ...totalStyle, halign:'right' }} }}]);

    checkPage(20);
    doc.setFontSize(FONT_SIZE + 2); doc.setFont("helvetica", "bold"); doc.text(nome, LEFT_MARGIN, y);
    doc.autoTable({{ startY: y + 3, head: [["Data","Attività","Abbonamento","Contanti","POS","Totale"]], body: body, styles: styles, headStyles: headStyles, tableWidth: TABLE_WIDTH, margin: {{ left: LEFT_MARGIN }}, columnStyles: {{ 3: numStyle, 4: numStyle, 5: numStyle }} }});
    y = doc.lastAutoTable.finalY + 10;
  }}

  // Ottengo sempre la lista istruttori ordinata secondo homeSortState
  const sortedInstructors = getSortedInstructors();

  if (mode === 'sintetico') {{
    if (currentInstructor) {{
        // Stampa dettaglio singolo (ordinato da getSortedDetails dentro addTable)
        addTable(currentInstructor);
    }} else {{
       // Stampa riepilogo (ordinato da sortedInstructors)
       const rows = [];
       let sc=0, sp=0, st=0;
       sortedInstructors.forEach(n => {{
           const i = DATA[key].istruttori[n];
           rows.push([n, euro(i.contanti), euro(i.pos), euro(i.totale)]);
           sc+=i.contanti; sp+=i.pos; st+=i.totale;
       }});
       rows.push([{{ content:'TOTALE', styles: totalStyle }}, {{ content:euro(sc), styles: {{ ...totalStyle, halign:'right' }} }}, {{ content:euro(sp), styles: {{ ...totalStyle, halign:'right' }} }}, {{ content:euro(st), styles: {{ ...totalStyle, halign:'right' }} }}]);
       doc.setFontSize(16); doc.text(getNiceTitle(key), 105, y, {{align: 'center'}});
       doc.autoTable({{ startY: y + 10, head: [["Istruttore","Contanti","POS","Totale"]], body: rows, styles: styles, headStyles: headStyles, tableWidth: TABLE_WIDTH, margin: {{ left: LEFT_MARGIN }}, columnStyles: {{ 1: numStyle, 2: numStyle, 3: numStyle }} }});
    }}
  }} else {{
      // PDF COMPLETO
      // 1. Riepilogo (Ordinato secondo homeSortState)
      let rows = []; let sc=0, sp=0, st=0;
      sortedInstructors.forEach(n => {{
           const i = DATA[key].istruttori[n];
           rows.push([n, euro(i.contanti), euro(i.pos), euro(i.totale)]);
           sc+=i.contanti; sp+=i.pos; st+=i.totale;
      }});
      rows.push([{{ content:'TOTALE', styles: totalStyle }}, {{ content:euro(sc), styles: {{ ...totalStyle, halign:'right' }} }}, {{ content:euro(sp), styles: {{ ...totalStyle, halign:'right' }} }}, {{ content:euro(st), styles: {{ ...totalStyle, halign:'right' }} }}]);
      doc.setFontSize(16); doc.text(getNiceTitle(key), 105, y, {{align: 'center'}});
      doc.autoTable({{ startY: y + 10, head: [["Istruttore","Contanti","POS","Totale"]], body: rows, styles: styles, headStyles: headStyles, tableWidth: TABLE_WIDTH, margin: {{ left: LEFT_MARGIN }}, columnStyles: {{ 1: numStyle, 2: numStyle, 3: numStyle }} }});
      y = doc.lastAutoTable.finalY + 15;
      
      // 2. Dettagli (TUTTI ordinati secondo detailSortState)
      sortedInstructors.forEach(n => addTable(n));
  }}
  window.open(doc.output('bloburl'));
}}

input.addEventListener("change", onPeriodChange);
renderHome(); // Avvio iniziale
</script>
</body>
</html>
"""
    with open(FILE_OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    periodo = None
    if len(sys.argv) > 1:
        m = re.match(r'^(\d{2})-(\d{4})$', sys.argv[1])
        if m: periodo = f"{m.group(2)}-{m.group(1)}"

    df = carica_dati()
    struttura = build_structure(df)

    if not struttura:
        genera_html({}, "2000-01", "2000-01", "2000-01")
        print("Nessun dato.")
    else:
        periodi = sorted(struttura.keys())
        p_def = periodo if (periodo and periodo in struttura) else periodi[-1]
        genera_html(struttura, p_def, periodi[0], periodi[-1])
        print(f"Generato: {FILE_OUTPUT_HTML}")
        
    try:
        webbrowser.open(f'file://{os.path.abspath(FILE_OUTPUT_HTML)}')
    except: pass

if __name__ == "__main__":
    main()