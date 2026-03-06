import sys
import re
import subprocess
import os
import asyncio
import edge_tts
import io
import tempfile
import shutil
import time

# msvcrt e pygame sono disponibili solo su Windows (riproduzione diretta)
ON_WINDOWS = os.name == 'nt'
if ON_WINDOWS:
    import msvcrt
    import pygame.mixer

# ── Configurazione velocità ──────────────────────────────────────────────────
# Aumenta MAX_CONCURRENT per più velocità (rischio 403 più alto)
# Valori consigliati: 3 (sicuro) | 5 (veloce) | 8 (massimo)
MAX_CONCURRENT = 5
# Path stacchetto: cerca prima nella stessa cartella dello script, poi il path Windows originale
_script_dir = os.path.dirname(os.path.abspath(__file__))
STACCHETTO_MP3 = os.path.join(_script_dir, "Chitarra.mp3")
if not os.path.exists(STACCHETTO_MP3):
    STACCHETTO_MP3 = r"C:\Dropbox\Prog\Buongiorno\Chitarra.mp3"
RETRY_DELAY    = 0.5      # Secondi tra un retry e l'altro (era 2.0+)
MAX_RETRIES    = 6        # Tentativi per frase
# ─────────────────────────────────────────────────────────────────────────────

MAX_TTS_CHARS  = 700   # Edge TTS fallisce oltre ~800 caratteri - splittiamo prima

_tts_semaphore = None

def _get_semaphore():
    global _tts_semaphore
    if _tts_semaphore is None:
        _tts_semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    return _tts_semaphore


def _frase_valida(testo: str) -> bool:
    """Scarta frasi troppo corte o composte solo da punteggiatura/spazi."""
    if testo == "__STACCHETTO__":
        return True
    lettere = sum(1 for c in testo if c.isalpha())
    return lettere >= 3

def _split_frase_lunga(testo: str, max_chars: int = MAX_TTS_CHARS) -> list:
    """
    Se il testo supera max_chars, lo divide in segmenti più corti
    spezzando sui separatori naturali (. ; , ) mantenendo ogni pezzo sotto il limite.
    """
    if len(testo) <= max_chars:
        return [testo]

    segmenti = []
    # Prova prima a spezzare sui punti
    for sep in ['. ', '; ', ', ', ' ']:
        parti = testo.split(sep)
        corrente = ''
        for p in parti:
            candidato = corrente + (sep if corrente else '') + p
            if len(candidato) <= max_chars:
                corrente = candidato
            else:
                if corrente:
                    segmenti.append(corrente.strip())
                corrente = p
        if corrente:
            segmenti.append(corrente.strip())
        # Verifica che tutti i segmenti siano sotto il limite
        if all(len(s) <= max_chars for s in segmenti) and segmenti:
            return [s for s in segmenti if _frase_valida(s)]

    # Fallback: tronca brutalmente
    return [testo[i:i+max_chars].strip() for i in range(0, len(testo), max_chars)]


async def generate_audio(text, voice, speed_rate="1.0", style=None):
    """
    Genera audio TTS per una singola frase.
    Ottimizzazione chiave: NESSUN sleep dopo successo (era il killer delle performance).
    Usa semaforo per limitare le connessioni parallele verso Microsoft.
    """
    sem = _get_semaphore()
    speed_float  = float(speed_rate)
    rate_percent = int((speed_float - 1.0) * 100)
    rate   = f"{rate_percent:+d}%"
    pitch  = "+0Hz"
    volume = "+0%"

    if style == 'cheerful':
        pitch = "+50Hz";  volume = "+20%"; rate = f"{int(rate_percent * 1.1):+d}%"
    elif style == 'sad':
        pitch = "-50Hz";  volume = "-10%"; rate = f"{int(rate_percent * 0.9):+d}%"
    elif style == 'angry':
        pitch = "+100Hz"; volume = "+30%"; rate = f"{int(rate_percent * 1.2):+d}%"
    elif style == 'fearful':
        pitch = "-20Hz";  volume = "-20%"; rate = f"{int(rate_percent * 0.95):+d}%"

    for attempt in range(MAX_RETRIES):
        try:
            async with sem:
                tts = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
                buf = bytearray()
                async for chunk in tts.stream():
                    if chunk["type"] == "audio":
                        buf.extend(chunk["data"])

            if not buf:
                raise ValueError("Nessun dato audio ricevuto.")

            return bytes(buf)   # <-- NESSUN sleep qui! Era il vero collo di bottiglia.

        except Exception as e:
            delay = RETRY_DELAY * (2 ** attempt)
            print(f"  TTS '{text[:40]}' tentativo {attempt+1}/{MAX_RETRIES}: riprovo in {delay:.1f}s", file=sys.stderr)
            await asyncio.sleep(delay)

    print(f"ERRORE DEFINITIVO: '{text[:40]}' fallito.", file=sys.stderr)
    return None


async def generate_all_audio(frasi_con_parametri, voce_femminile, voce_maschile):
    """
    Genera TUTTE le frasi in parallelo, limitate dal semaforo.
    Restituisce lista ordinata [(audio_bytes|None, pause), ...].
    """
    async def task(idx, frase, voce_mode, speed, pause, style):
        if frase == "__STACCHETTO__":
            return idx, "__STACCHETTO__", pause  # nessuna generazione TTS
        if voce_mode == "X":
            voce = voce_femminile if idx % 2 == 1 else voce_maschile
        elif voce_mode == "M":
            voce = voce_maschile
        else:
            voce = voce_femminile
        audio = await generate_audio(frase, voce, speed, style)
        return idx, audio, pause

    # Espandi frasi troppo lunghe per Edge TTS
    frasi_espanse = []
    for (frase, vm, sp, pause, st) in frasi_con_parametri:
        if frase == "__STACCHETTO__":
            frasi_espanse.append((frase, vm, sp, pause, st))
        else:
            segmenti = _split_frase_lunga(frase)
            for j, seg in enumerate(segmenti):
                # La pausa va solo all'ultimo segmento
                p = pause if j == len(segmenti) - 1 else 0
                frasi_espanse.append((seg, vm, sp, p, st))

    tasks = [
        asyncio.create_task(task(i, frase, vm, sp, pause, st))
        for i, (frase, vm, sp, pause, st) in enumerate(frasi_espanse)
    ]

    total   = len(tasks)
    results = [None] * total
    done    = 0

    for coro in asyncio.as_completed(tasks):
        idx, audio, pause = await coro
        results[idx] = (audio, pause)
        done += 1
        if done % 10 == 0 or done == total:
            pct = done * 100 // total
            bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
            print(f"  [{bar}] {done}/{total} ({pct}%)")

    return results


def _create_silence_mp3(path, duration):
    cmd = ['ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo',
           '-t', str(duration), '-c:a', 'libmp3lame', '-b:a', '64k', '-y', path]
    subprocess.run(cmd, capture_output=True, timeout=15)


def assemble_mp3(results, output_file, temp_dir):
    """Assembla i file audio in ordine con FFmpeg (copia diretta, no re-encode)."""
    chunk_files = []
    for idx, item in enumerate(results):
        if item is None or item[0] is None:
            continue
        audio, pause = item
        if audio == "__STACCHETTO__":
            # Inserisce il file Chitarra.mp3 come stacchetto musicale
            if os.path.exists(STACCHETTO_MP3):
                chunk_files.append(STACCHETTO_MP3)
            else:
                print(f"AVVISO: stacchetto non trovato: {STACCHETTO_MP3}", file=sys.stderr)
            continue
        fpath = os.path.join(temp_dir, f"f_{idx:05d}.mp3")
        with open(fpath, "wb") as f:
            f.write(audio)
        chunk_files.append(fpath)
        if pause > 0:
            sp = os.path.join(temp_dir, f"p_{idx:05d}.mp3")
            _create_silence_mp3(sp, pause)
            chunk_files.append(sp)

    if not chunk_files:
        print("Nessun file audio da assemblare.", file=sys.stderr)
        return False

    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for fp in chunk_files:
            f.write(f"file '{fp.replace(os.sep, '/')}'\n")

    # Usa re-encode per garantire compatibilità tra file di sorgenti diverse
    # (Edge TTS e file MP3 esterni come Chitarra.mp3 possono avere sample rate diversi)
    cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file,
           '-ar', '44100', '-ac', '2', '-c:a', 'libmp3lame', '-b:a', '192k',
           '-y', output_file]
    print(f"  Assemblaggio FFmpeg ({len(chunk_files)} file)...")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        print(f"FFmpeg errore:\n{proc.stderr}", file=sys.stderr)
        return False
    return os.path.exists(output_file)


def mix_with_background(voice_file, background_file, output_file, volume=-5):
    if not os.path.exists(voice_file) or not os.path.exists(background_file):
        print("File mancante per mixaggio.", file=sys.stderr)
        return False
    cmd_dur = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', voice_file]
    res = subprocess.run(cmd_dur, capture_output=True, text=True, timeout=10)
    if res.returncode != 0:
        return False
    voice_duration = float(res.stdout.strip())
    total_duration = voice_duration + 20
    filter_complex = (
        f"[1:a]atrim=0:{total_duration},"
        f"afade=t=in:st=0:d=3,"
        f"afade=t=out:st={total_duration-10}:d=10,"
        f"volume={volume}dB[bg];"
        "[0:a]volume=6.0dB,adelay=10000|10000[voice];"
        "[bg][voice]amix=inputs=2:duration=first[out]"
    )
    cmd = ['ffmpeg', '-i', voice_file, '-stream_loop', '-1', '-i', background_file,
           '-filter_complex', filter_complex, '-map', '[out]',
           '-t', str(total_duration), '-c:a', 'libmp3lame', '-b:a', '192k',
           '-threads', str(os.cpu_count() or 4), '-y', output_file]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return proc.returncode == 0 and os.path.exists(output_file)


def print_parameters_help():
    print("\n" + "-" * 51)
    print("F = voce femminile")
    print("M = voce maschile")
    print("X = voce alternata")
    print("V = crea Lettura.mp3")
    print("B = base musicale in Lettura.mp3")
    print("Sn.n = Velocità (normale = S1.0)")
    print("Pn.n = Pausa di n.n secondi")
    print("SA = Allegro | ST = Triste | AN = Arrabbiato | SP = Spaventato")
    print("-" * 51)


async def speak_text_fast(text, voice_name, speed_rate="1.0", style=None, initial_delay=0.1):
    if not ON_WINDOWS:
        return
    audio_data = await generate_audio(text, voice_name, speed_rate, style)
    if audio_data:
        audio_buffer = io.BytesIO(audio_data)
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.music.stop()
        pygame.mixer.music.load(audio_buffer)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.02)


async def leggi_file_con_voci_optimized(nome_file, parametri):
    stili_emotivi = {'SA': 'cheerful', 'ST': 'sad', 'AN': 'angry', 'SP': 'fearful'}
    parametri = [p.upper() for p in parametri]

    voice_mode     = "X" if "X" in parametri else ("M" if "M" in parametri else "F")
    salva_in_mp3   = "V" in parametri
    usa_sottofondo = "B" in parametri

    if usa_sottofondo and not salva_in_mp3:
        print("ATTENZIONE: B richiede V. Abilitando salvataggio MP3.")
        salva_in_mp3 = True

    speed_param = next((p for p in parametri if p.startswith('S') and p[1:].replace('.','',1).isdigit()), None)
    speed_rate  = "1.0"
    if speed_param:
        try:
            sv = float(speed_param[1:])
            if 0.1 <= sv <= 3.0:
                speed_rate = str(sv)
        except ValueError:
            pass

    voce_femminile = "it-IT-ElsaNeural"
    voce_maschile  = "it-IT-DiegoNeural"

    try:
        with open(nome_file, "r", encoding="utf-8") as f:
            testo = f.read()
    except FileNotFoundError:
        print(f"ERRORE: il file '{nome_file}' non esiste.", file=sys.stderr); return
    except Exception as e:
        print(f"ERRORE leggendo '{nome_file}': {e}", file=sys.stderr); return

    testo = re.sub(r'^[\s.?!]+', '', testo, flags=re.MULTILINE)
    testo = re.sub(r'!+', '!', testo)
    testo = re.sub(r'\?+', '?', testo)
    testo = re.sub(r'([^.,!?])\n', r'\1.\n', testo)
    testo = testo.replace("\n", " ")
    testo = testo.replace("\\", "")

    current_voice = voice_mode
    current_speed = speed_rate
    current_style = None
    frasi_con_parametri = []
    frase_corrente = ""

    i = 0
    while i < len(testo):
        if testo[i] == '[':
            end_bracket = testo.find(']', i)
            if end_bracket != -1:
                marker = testo[i:end_bracket+1]
                if frase_corrente.strip() and _frase_valida(frase_corrente.strip()):
                    frasi_con_parametri.append((frase_corrente.strip(), current_voice, current_speed, 0, current_style))
                    frase_corrente = ""
                if marker == '[F]':
                    current_voice = 'F'
                elif marker == '[M]':
                    current_voice = 'M'
                elif marker == '[X]':
                    current_voice = 'X'
                elif marker == '[T]':
                    # Stacchetto musicale: salva la frase corrente e inserisce marker speciale
                    if frase_corrente.strip() and _frase_valida(frase_corrente.strip()):
                        frasi_con_parametri.append((frase_corrente.strip(), current_voice, current_speed, 0, current_style))
                        frase_corrente = ""
                    frasi_con_parametri.append(("__STACCHETTO__", current_voice, current_speed, 0, None))
                else:
                    stile_match = re.match(r'\[S([A-Z]+)\]', marker)
                    if stile_match:
                        current_style = stili_emotivi.get(stile_match.group(1))
                    else:
                        speed_match = re.match(r'\[S(\d+(\.\d+)?)\]', marker)
                        if speed_match:
                            try:
                                sv = float(speed_match.group(1))
                                if 0.1 <= sv <= 3.0:
                                    current_speed = str(sv)
                            except ValueError:
                                pass
                        else:
                            pause_match = re.match(r'\[P(\d+(\.\d+)?)\]', marker)
                            if pause_match:
                                try:
                                    pv = float(pause_match.group(1))
                                    if not frase_corrente.strip() and not frasi_con_parametri:
                                        frasi_con_parametri.append((" ", current_voice, current_speed, pv, current_style))
                                    elif frase_corrente.strip() and _frase_valida(frase_corrente.strip()):
                                        frasi_con_parametri.append((frase_corrente.strip(), current_voice, current_speed, pv, current_style))
                                        frase_corrente = ""
                                    else:
                                        if frasi_con_parametri:
                                            f2, v2, s2, _, st2 = frasi_con_parametri[-1]
                                            frasi_con_parametri[-1] = (f2, v2, s2, pv, st2)
                                        else:
                                            frasi_con_parametri.append((" ", current_voice, current_speed, pv, current_style))
                                except ValueError:
                                    pass
                i = end_bracket + 1
                continue

        elif testo[i] in '.!?':
            frase_corrente += testo[i]
            if frase_corrente.strip() and _frase_valida(frase_corrente.strip()):
                frasi_con_parametri.append((frase_corrente.strip(), current_voice, current_speed, 0, current_style))
                frase_corrente = ""
            current_style = None
        else:
            frase_corrente += testo[i]
        i += 1

    if frase_corrente.strip() and _frase_valida(frase_corrente.strip()):
        frasi_con_parametri.append((frase_corrente.strip(), current_voice, current_speed, 0, current_style))

    print(f"Processando {len(frasi_con_parametri)} frasi con {MAX_CONCURRENT} richieste parallele...")

    # ── MODALITÀ MP3 ─────────────────────────────────────────────────────────
    if salva_in_mp3:
        print(f"MODALITA' VELOCE | parallelo={MAX_CONCURRENT} | retry_delay={RETRY_DELAY}s")
        start_time = time.time()
        temp_audio_dir = None
        try:
            temp_audio_dir = tempfile.mkdtemp(prefix="audio_tts_")

            results = await generate_all_audio(frasi_con_parametri, voce_femminile, voce_maschile)

            gen_time = time.time() - start_time
            ok = sum(1 for r in results if r and r[0])
            print(f"Generazione: {ok}/{len(results)} frasi OK in {gen_time:.1f}s")

            temp_voice_file = os.path.join(temp_audio_dir, "voice_temp.mp3")
            if assemble_mp3(results, temp_voice_file, temp_audio_dir):
                final_file = "Lettura.mp3"
                if usa_sottofondo:
                    print("Aggiungendo sottofondo musicale...")
                    base_mp3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Base.mp3")
                    if mix_with_background(temp_voice_file, base_mp3, final_file):
                        print("File con sottofondo creato!")
                    else:
                        print("Errore sottofondo, uso file vocale.", file=sys.stderr)
                        shutil.copy(temp_voice_file, final_file)
                else:
                    if os.path.exists(final_file):
                        os.remove(final_file)
                    shutil.copy(temp_voice_file, final_file)
                    print("File audio creato!")

                elapsed = time.time() - start_time
                frasi_s = len(frasi_con_parametri) / elapsed if elapsed > 0 else 0
                print(f"COMPLETATO in {elapsed:.1f}s | {frasi_s:.1f} frasi/s")
            else:
                print("Errore nell'assemblaggio.", file=sys.stderr)

        except Exception as e:
            print(f"ERRORE MP3: {e}", file=sys.stderr)
        finally:
            if temp_audio_dir and os.path.exists(temp_audio_dir):
                shutil.rmtree(temp_audio_dir, ignore_errors=True)

    # ── MODALITÀ RIPRODUZIONE DIRETTA ─────────────────────────────────────────
    else:
        if not ON_WINDOWS:
            print("ERRORE: riproduzione diretta non supportata su questo sistema.", file=sys.stderr)
            return
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            except Exception as e:
                print(f"ERRORE mixer: {e}", file=sys.stderr); return

        for i, (frase, voce_mode, speed, pause, style) in enumerate(frasi_con_parametri, start=1):
            if ON_WINDOWS and msvcrt.kbhit() and msvcrt.getch() == b'\x1b':
                print("\nInterruzione da utente.")
                print_parameters_help()
                sys.exit(0)

            voce_corrente = voce_femminile if voce_mode != "M" else voce_maschile
            if voce_mode == "X":
                voce_corrente = voce_femminile if i % 2 == 1 else voce_maschile

            genere = "[M]" if voce_corrente == voce_maschile else "[F]"
            stile_codice = next((k for k, v in stili_emotivi.items() if v == style), '')
            print(f"{genere} {frase}" + (f" [S{stile_codice}]" if stile_codice else "") + (f" [P{pause}]" if pause > 0 else ""))

            if frase == "__STACCHETTO__":
                # Riproduci stacchetto musicale
                if os.path.exists(STACCHETTO_MP3):
                    print("[T] Stacchetto musicale")
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    pygame.mixer.music.stop()
                    pygame.mixer.music.load(STACCHETTO_MP3)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.05)
                else:
                    print(f"AVVISO: stacchetto non trovato: {STACCHETTO_MP3}", file=sys.stderr)
            else:
                await speak_text_fast(frase, voce_corrente, speed, style)
            if pause > 0:
                await asyncio.sleep(pause)

        if ON_WINDOWS and pygame.mixer.get_init():
            pygame.mixer.quit()

    print_parameters_help()


def main():
    try:
        import psutil
        p = psutil.Process()
        p.nice(psutil.HIGH_PRIORITY_CLASS if os.name == 'nt' else -10)
        print(f"INFO: Priorità del processo impostata a {p.nice()}.")
    except Exception as e:
        print(f"AVVISO: priorità non impostata: {e}", file=sys.stderr)

    parametri = sys.argv[1:]
    asyncio.run(leggi_file_con_voci_optimized("Lettura.txt", parametri))


if __name__ == "__main__":
    main()
