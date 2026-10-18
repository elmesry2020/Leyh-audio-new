# -*- coding: utf-8 -*-
"""يولّد mp3 بصوت حامد لكل نص في manifest.json ويسميه بنفس hash الذي يطلبه التطبيق.
الاستخدام: python tts/generate_all.py --out Leyh-audio/a --shard 0 --of 8 [--kinds hadith,scene] [--force]"""
import argparse, asyncio, html, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import prepare, CFG

def chunks(text, limit=1800):
    parts, cur = [], ''
    for s in re.split(r'(?<=[.؟?!،])\s+', text):
        if cur and len(cur) + len(s) + 1 > limit: parts.append(cur); cur = s
        else: cur = (cur + ' ' + s).strip()
        while len(cur) > limit:
            cut = cur.rfind(' ', 0, limit); cut = cut if cut > 0 else limit
            parts.append(cur[:cut]); cur = cur[cut:].strip()
    if cur: parts.append(cur)
    return parts

def azure_request(text):
    """Synthesize with the official Azure Speech REST API. Credentials come from env."""
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if not key or not region:
        raise RuntimeError("Azure requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
    voice = os.environ.get("AZURE_SPEECH_VOICE", CFG["voice"]).strip()
    # XML-escape the prepared text; never interpolate raw text into SSML.
    xml_text = html.escape(text, quote=False)
    ssml = (f'<speak version="1.0" xml:lang="ar-SA"><voice name="{html.escape(voice, quote=True)}">'
            f'{xml_text}</voice></speak>').encode("utf-8")
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    req = urllib.request.Request(url, data=ssml, headers={
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml; charset=utf-8",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "LeyhQalha-TTS/1.0",
    }, method="POST")
    with urllib.request.urlopen(req, timeout=90) as response:
        audio = response.read()
        if response.status != 200 or len(audio) <= 500:
            raise RuntimeError(f"Azure returned invalid audio (HTTP {response.status}, {len(audio)} bytes)")
        return audio

async def synth(text, path, retries=6, provider="auto"):
    has_azure = bool(os.environ.get("AZURE_SPEECH_KEY", "").strip() and
                     os.environ.get("AZURE_SPEECH_REGION", "").strip())
    chosen = ("azure" if has_azure else "edge") if provider == "auto" else provider
    if chosen == "azure" and not has_azure:
        raise RuntimeError("Selected Azure provider but AZURE_SPEECH_KEY / AZURE_SPEECH_REGION are missing")
    for i in range(retries):
        try:
            if chosen == "azure":
                audio = await asyncio.to_thread(azure_request, text)
                with open(path, "wb") as f: f.write(audio)
            else:
                import edge_tts  # loaded only for the unofficial fallback provider
                await edge_tts.Communicate(text, CFG["voice"], rate=CFG.get("rate", "+0%")).save(path)
            if os.path.getsize(path) > 500: return
            raise RuntimeError("TTS returned an empty or too-small audio file")
        except Exception as e:
            print(f"{chosen} retry {i + 1}/{retries}: {e}", file=sys.stderr)
        await asyncio.sleep(2 + 3 * i)
    raise RuntimeError(f"{chosen} synthesis failed")

async def make(item, outdir, sem, provider="auto"):
    final = os.path.join(outdir, item['h'] + '.mp3')
    async with sem:
        with tempfile.TemporaryDirectory() as td:
            files = []
            for n, part in enumerate(chunks(prepare(item['t']))):
                p = os.path.join(td, f'{n:03d}.mp3'); await synth(part, p, provider=provider); files.append(p)
            lst = os.path.join(td, 'l.txt'); open(lst, 'w').write(''.join(f"file '{p}'\n" for p in files))
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                            '-ac', '1', '-ar', '24000', '-b:a', '32k', final + '.tmp.mp3'], check=True)
            os.replace(final + '.tmp.mp3', final)
    print('ok', item['h'], item['k'], flush=True)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--of', type=int, default=1); ap.add_argument('--kinds', default='hadith,scene')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--conc', type=int, default=4)
    ap.add_argument('--provider', choices=['auto','azure','edge'], default='auto', help='auto selects Azure when credentials are set; otherwise edge-tts')
    ap.add_argument('--limit', type=int, default=0, help='process at most N missing files in this shard (0 = all)')
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    kinds = a.kinds.split(',')
    man = [m for m in json.load(open(os.path.join(os.path.dirname(__file__), 'manifest.json'), encoding='utf8')) if m['k'] in kinds]
    mine = [m for i, m in enumerate(man) if i % a.of == a.shard]
    todo = [m for m in mine if a.force or not os.path.exists(os.path.join(a.out, m['h'] + '.mp3'))]
    if a.limit > 0: todo = todo[:a.limit]
    print(f'shard {a.shard}/{a.of}: {len(todo)} to do of {len(mine)}', flush=True)
    sem = asyncio.Semaphore(a.conc)
    print('provider:', ('azure' if (a.provider == 'azure' or (a.provider == 'auto' and os.environ.get('AZURE_SPEECH_KEY') and os.environ.get('AZURE_SPEECH_REGION'))) else 'edge-tts'), flush=True)
    res = await asyncio.gather(*[make(m, a.out, sem, a.provider) for m in todo], return_exceptions=True)
    bad = [r for r in res if isinstance(r, Exception)]
    print('failed:', len(bad)); sys.exit(1 if bad else 0)
asyncio.run(main())
