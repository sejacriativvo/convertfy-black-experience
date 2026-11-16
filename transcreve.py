"""transcreve.py: Whisper large-v3 (MLX) nos clipes da FX30 que ainda não estão na transcrição (dia 11 e dia 12, até 1420).
Saída: dados/transcricao.json {"breno.NNNN": [segmentos com words]}. Clipe que não está em bruto/ fica pra depois."""
import os, json, subprocess, time, glob
import mlx_whisper
AQUI = os.path.dirname(os.path.abspath(__file__))
import fontes
OUT = os.path.join(fontes.DADOS, "transcricao.json")
t = json.load(open(OUT))
alvo = [f"breno.{n}" for n in range(1168, 1421)]
while True:
    falta = [k for k in alvo if k not in t]
    if not falta: break
    feito = False
    for k in falta:
        f = os.path.join(fontes.BRUTO, fontes.relativo_bruto(int(k[6:])))
        if not os.path.exists(f): continue
        tem_som = subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=index","-of","csv=p=0",f],
                                 capture_output=True, text=True).stdout.strip()
        if not tem_som:
            t[k] = []; json.dump(t, open(OUT, "w"), ensure_ascii=False); continue
        wav = f"/tmp/_tr_{k}.wav"
        subprocess.run(["ffmpeg","-v","error","-y","-i",f,"-map","0:a:0","-ac","1","-ar","16000",wav], check=True)
        r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-mlx", language="pt",
                                   word_timestamps=True, condition_on_previous_text=False)
        os.remove(wav)
        t[k] = r["segments"]; json.dump(t, open(OUT, "w"), ensure_ascii=False)
        print(k, " ".join(s["text"] for s in r["segments"])[:150], flush=True); feito = True
    if not feito:
        break
print("FIM", flush=True)
