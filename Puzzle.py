# -*- coding: utf-8 -*-
"""
Puzzle.py — fix dialog: input non sborda + Invio conferma
Autore: Nino Mazzarisi — 28/10/2025
"""

import csv, json, random
from pathlib import Path

CSV_FILENAME = "Dimensioni rettangoli.csv"
TXT_FILENAME = "Nomi Famiglia Pricci.txt"
HTML_FILENAME = "Puzzle.html"

ICON_URL = "https://sebastiano-mazzarisi.github.io/Test/Puzzle.png"


# ---------------------------- IO ----------------------------
def leggi_csv(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        txt = f.read().strip()
        sep = "," if "," in txt.splitlines()[0] else ";"
    mappa = {}
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=sep)
        for r in reader:
            n = int(r["n_caratteri"])
            mappa[n] = {
                "totale_pezzi": int(r["totale_pezzi"]),
                "righe": int(r["righe"]),
                "colonne": int(r["colonne"]),
                "riempimento_at": int(r["tasti_di_riempimento_@"]),
                "vuoti_hash": int(r["tasto_vuoto_#"]),
            }
    return mappa


def leggi_nomi(path: Path):
    parole = [x.strip().upper() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    random.shuffle(parole)
    return parole


# ------------------------- GENERA HTML ------------------------
def genera_html(out_path: Path, mappa, parole):
    css = r"""
:root{
  --bg:#f9fafb;--panel:#fff;--accent:#2563eb;--bordo:#b3d4fc;
  --tile:#e6f0ff;--tile-at:#e5e7eb;--tile-empty:#ffedd5;
  --tile-border:#d1d5db;--shadow:0 6px 20px rgba(0,0,0,.08);
  --radius:18px;--tile-radius:12px;--gap:4px;
  --tile-font:calc(1.8vw + 12px);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font-family:"Poppins",system-ui,sans-serif;
display:flex;flex-direction:column;align-items:center;justify-content:center;
min-height:100dvh;color:#1f2937;-webkit-user-select:none;user-select:none;
touch-action:manipulation;}
.app{width:95vw;max-width:500px;background:var(--panel);
border-radius:var(--radius);box-shadow:var(--shadow);
padding:18px;text-align:center;}
.title{font-size:17px;margin-bottom:12px;font-style:italic;font-weight:400;
color:#374151;user-select:none;}
.title span{cursor:pointer;}
.board-wrap{border:8px solid var(--bordo);border-radius:var(--radius);
padding:10px;margin:auto;display:inline-block;transition:border .3s ease, border-color .2s ease;}
.board-wrap.large-border{border-width:8px;}
.board{display:grid;gap:var(--gap);justify-content:center;align-content:center;
margin:auto;transition:grid-template-columns .2s ease;}
.tile{aspect-ratio:1/1;width:calc(19vw);max-width:65px;display:grid;
place-items:center;border-radius:var(--tile-radius);
font-weight:700;font-size:var(--tile-font);
user-select:none;border:1px solid var(--tile-border);
transition:transform .1s;}
.tile.letter{background:var(--tile);color:#0f172a;}
.tile.at{background:var(--tile-at);color:transparent;}
.tile.empty{background:var(--tile-empty);border-style:dashed;color:#fb923c;}
.tile.clickable:active{transform:scale(.96);}
.controls{display:flex;justify-content:center;gap:10px;margin-top:16px;flex-wrap:wrap;}
button{border:1px solid #e5e7eb;background:#fff;padding:10px 14px;border-radius:12px;
cursor:pointer;transition:.15s;box-shadow:0 3px 8px rgba(0,0,0,0.05);
font-weight:600;font-size:16px;}
button:active{transform:scale(.96);}
button.primary{background:var(--accent);color:#fff;border:none;}
@keyframes frameflash{
  0%{border-color:#3b82f6;}
  20%{border-color:#ef4444;}
  40%{border-color:#facc15;}
  60%{border-color:#22c55e;}
  80%{border-color:#06b6d4;}
  100%{border-color:#3b82f6;}
}
.flash-border{animation:frameflash 0.8s linear 5;}

/* Dialog */
.dialog-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.4);display:none;
justify-content:center;align-items:center;z-index:999;padding:16px;}
.dialog{background:#fff;border-radius:12px;padding:16px 16px 12px 16px;
width:100%;max-width:360px;text-align:center;box-shadow:0 6px 25px rgba(0,0,0,0.3);}
.dialog .label{font-size:14px;color:#374151;margin-bottom:8px;}
.dialog input{width:100%;padding:10px 12px;border:1px solid #d1d5db;border-radius:8px;
font-size:17px; /* >=16 per evitare zoom su iPhone */
outline:none;}
.dialog .btns{display:flex;justify-content:center;gap:10px;margin-top:10px;}
.dialog button{margin:0;padding:8px 16px;border-radius:8px;font-weight:600;}
.dialog .ok{background:var(--accent);color:#fff;border:none;}
.dialog .cancel{background:#f3f4f6;border:1px solid #ddd;}
"""

    js = r"""
(() => {
  // -------------------- Stato/elementi --------------------
  const data = JSON.parse(document.getElementById("puzzle-data").textContent);
  const paroleBase = data.parole.slice();
  const mappa = data.mappa;

  const board = document.querySelector(".board");
  const frame = document.querySelector(".board-wrap");
  const btnShuffle = document.querySelector("#shuffle");
  const btnSolve = document.querySelector("#solve");
  const btnNext = document.querySelector("#next");

  const titoloPuzzle = document.querySelector(".t-puzzle");
  const titoloBy = document.querySelector(".t-by");
  const titoloMazzarisi = document.querySelector(".t-mazzarisi");

  const dialog = document.querySelector(".dialog-overlay");
  const inputFrase = document.querySelector("#frase");
  const okBtn = document.querySelector("#okBtn");
  const cancelBtn = document.querySelector("#cancelBtn");

  // Modalità: 'names' | 'numbers4' | 'numbers3' | 'custom'
  let mode = 'names';
  let shortNames = True = true; // (solo doc) manteniamo la variabile shortNames
  let short = true;             // effettivo flag per nomi corti
  let queue = [];
  let qIndex = 0;
  let currentWord = "";
  let current = [];
  let solution = [];
  let conf = null;
  let cols = 0;

  // -------------------- Audio --------------------
  let ctx = null;
  function ensureAudio(){ if(!ctx) ctx = new (window.AudioContext||window.webkitAudioContext)(); }
  function tick(){
    ensureAudio();
    const osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.type="square"; osc.frequency.value=240; gain.gain.value=0.06;
    osc.connect(gain); gain.connect(ctx.destination);
    osc.start(); gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.08);
    osc.stop(ctx.currentTime + 0.08);
  }
  function cheerLoop(duration=4){
    ensureAudio();
    const start = ctx.currentTime, end = start + duration;
    let t = start;
    while(t < end){
      const osc = ctx.createOscillator(), g = ctx.createGain();
      osc.type="sine";
      const f1 = 400 + Math.random()*1000, f2 = f1 + 600;
      osc.frequency.setValueAtTime(f1, t);
      osc.frequency.exponentialRampToValueAtTime(f2, t+0.25);
      g.gain.setValueAtTime(0.05, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t+0.3);
      osc.connect(g); g.connect(ctx.destination);
      osc.start(t); osc.stop(t+0.3); t += 0.3;
    }
  }

  // -------------------- Utility --------------------
  const disp = c => c===" " ? "·" : (c==="#"||c==="@"?"":c);
  const coord=(i,c)=>[Math.floor(i/c), i%c];
  const isSolved=(a,b)=>a.length===b.length && a.every((x,i)=>x===b[i]);
  const shuffle=a=>{ let arr=a.slice(); do{
    for(let i=arr.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1)); [arr[i],arr[j]]=[arr[j],arr[i]];}
  }while(isSolved(arr,a)); return arr; };
  const nearestConf = n => {
    const keys=Object.keys(mappa).map(Number);
    let best=keys[0];
    for(const k of keys){ if(Math.abs(k-n) < Math.abs(best-n)) best=k; }
    return mappa[best];
  };

  // -------------------- Costruttori --------------------
  function buildFromText(txt){
    currentWord = txt;
    const n = [...txt].length;
    conf = mappa[n] || nearestConf(n);
    cols = conf.colonne;
    solution = [...txt, ...Array(conf.riempimento_at).fill("@"), ...Array(conf.vuoti_hash).fill("#")];
    current = shuffle(solution);
    render();
  }

  function buildNumbers(size){ // 4 => 1..15, 3 => 1..8
    mode = (size===4?'numbers4':'numbers3');
    const max = size*size - 1;
    const numbers = Array.from({length:max}, (_,i)=>(i+1).toString());
    solution = [...numbers, "#"];
    current = shuffle(solution);
    conf = { colonne:size, righe:size, riempimento_at:0, vuoti_hash:1 };
    cols = size;
    currentWord = numbers.join("");
    render();
  }

  function setNamesMode(shortWanted=true){
    mode='names'; short = shortWanted;
    const base = paroleBase.slice();
    const list = short ? base.map(p => {
      const i = p.indexOf(" "); return i>=0 ? p.slice(i+1).trim() : p;
    }) : base;
    // coda random senza ripetizioni
    queue = list.slice();
    for(let i=queue.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1)); [queue[i],queue[j]]=[queue[j],queue[i]];}
    qIndex = 0;
    frame.classList.toggle("large-border", short);
    buildFromText(queue[qIndex]);
  }

  function setCustom(txt){
    mode='custom';
    frame.classList.remove("large-border");
    buildFromText(txt);
  }

  // -------------------- Render & move --------------------
  function render(){
    board.style.gridTemplateColumns=`repeat(${conf.colonne},1fr)`;
    board.innerHTML="";
    current.forEach((v,i)=>{
      const d=document.createElement("div");
      d.className = "tile " + (v==="#"?"empty":(v==="@"?"at":"letter")) + " clickable";
      d.textContent = disp(v);
      d.onclick = () => move(i);
      board.appendChild(d);
    });
  }

  function move(i){
    const e = current.indexOf("#");
    if(e<0 || i===e) return;
    const [rE,cE]=coord(e,cols), [rI,cI]=coord(i,cols);
    if(rE===rI){
      const dir=cI<cE?1:-1;
      for(let c=cE-dir;c!==cI-dir;c-=dir){const a=rE*cols+c, b=rE*cols+c+dir; [current[a],current[b]]=[current[b],current[a]];}
    } else if(cE===cI){
      const dir=rI<rE?1:-1;
      for(let r=rE-dir;r!==rI-dir;r-=dir){const a=r*cols+cE, b=(r+dir)*cols+cE; [current[a],current[b]]=[current[b],current[a]];}
    } else return;
    tick(); render();
    if(isSolved(current,solution)){
      cheerLoop(4);
      frame.classList.add("flash-border");
      setTimeout(()=>frame.classList.remove("flash-border"),4000);
    }
  }

  // -------------------- Bottoni --------------------
  btnShuffle.onclick=()=>{ current = shuffle(solution); render(); };
  btnSolve.onclick=()=>{ current = solution.slice(); render(); };

  btnNext.onclick=()=>{
    if(mode==='numbers4' || mode==='numbers3' || mode==='custom'){
      current = shuffle(solution); render(); return;
    }
    // nomi
    qIndex++;
    if(qIndex >= queue.length){
      queue = queue.slice();
      for(let i=queue.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1)); [queue[i],queue[j]]=[queue[j],queue[i]];}
      qIndex = 0;
    }
    buildFromText(queue[qIndex]);
  };

  // -------------------- Titolo --------------------
  titoloPuzzle.onclick=()=>{
    if(mode==='numbers4'){ buildNumbers(3); return; }
    if(mode==='numbers3'){ buildNumbers(4); return; }
    setNamesMode(!short);
  };
  titoloBy.onclick=()=>{ buildNumbers(4); };
  titoloMazzarisi.onclick=()=>{
    inputFrase.value="";
    dialog.style.display="flex";
    inputFrase.focus();
  };

  // Invio = conferma
  inputFrase.addEventListener("keydown", (e)=>{
    if(e.key === "Enter"){
      e.preventDefault();
      okBtn.click();
    }
  });

  okBtn.onclick=()=>{
    const frase = inputFrase.value.trim().toUpperCase();
    dialog.style.display="none";
    if(!frase) return;
    setCustom(frase);
  };
  cancelBtn.onclick=()=>{ dialog.style.display="none"; };

  // -------------------- Avvio --------------------
  setNamesMode(true);
})();
"""

    data_json = json.dumps({"parole": parole, "mappa": mappa}, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Puzzle">
<link rel="apple-touch-icon" href="{ICON_URL}">
<link rel="icon" type="image/png" href="{ICON_URL}">
<meta name="theme-color" content="#2563eb">
<title>Puzzle by Mazzarisi</title>
<style>{css}</style>
</head>
<body>
<div class="app">
  <div class="title"><span class="t-puzzle">Puzzle</span> <span class="t-by">by</span> <span class="t-mazzarisi">Mazzarisi</span></div>
  <div class="board-wrap">
    <div class="board"></div>
  </div>
  <div class="controls">
    <button id="shuffle">Mescola</button>
    <button id="solve">Soluzione</button>
    <button id="next" class="primary">Prossimo</button>
  </div>
</div>

<div class="dialog-overlay">
  <div class="dialog">
    <div class="label">Frase da ordinare:</div>
    <input type="text" id="frase" placeholder="scrivi qui...">
    <div class="btns">
      <button class="ok" id="okBtn">OK</button>
      <button class="cancel" id="cancelBtn">Esci</button>
    </div>
  </div>
</div>

<script id="puzzle-data" type="application/json">{json.dumps({"parole": parole, "mappa": mappa}, ensure_ascii=False)}</script>
<script>{js}</script>
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ Creato: {out_path}")


# --------------------------- MAIN ---------------------------
def main():
    base = Path(__file__).resolve().parent
    mappa = leggi_csv(base / CSV_FILENAME)
    parole = leggi_nomi(base / TXT_FILENAME)
    genera_html(base / HTML_FILENAME, mappa, parole)


if __name__ == "__main__":
    main()
