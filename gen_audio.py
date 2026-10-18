
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "tts" / "config.json").read_text(encoding="utf-8"))
VOICE = CFG["voice"]
RATE = CFG.get("rate", "+0%")
INPUT_FILE = ROOT / "leyh_texts_refreshed.json"
# التطبيق يقرأ التسجيلات من a/<id>.mp3
OUTPUT_DIR = ROOT / "a"
SHARD = int(os.getenv("SHARD", "0"))
SHARDS = int(os.getenv("SHARDS", "8"))


def safe_name(item):
    value = str(item.get("id", "")).strip()
    if not value:
        value = hashlib.sha1(
            str(item.get("tts_text", "")).encode("utf-8")
        ).hexdigest()[:20]
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)[:100]


async def main():
    if not INPUT_FILE.exists():
        raise SystemExit("Missing leyh_texts_refreshed.json")

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Expected a JSON list")

    OUTPUT_DIR.mkdir(exist_ok=True)
    selected = [
        item for index, item in enumerate(data)
        if index % SHARDS == SHARD
    ]

    print(f"Voice: {VOICE}; records: {len(selected)}")
    errors = []
    generated = 0

    for number, item in enumerate(selected, 1):
        text = str(item.get("tts_text") or "").strip()
        if not text:
            errors.append(f"{item.get('id', '?')}: empty text")
            continue

        target = OUTPUT_DIR / (safe_name(item) + ".mp3")

        try:
            await edge_tts.Communicate(
                text, VOICE, rate=RATE
            ).save(str(target))

            if not target.exists() or target.stat().st_size < 1000:
                raise RuntimeError("MP3 missing or too small")

            generated += 1

        except Exception as error:
            errors.append(f"{item.get('id', '?')}: {error}")
            if target.exists():
                target.unlink()

        if number % 25 == 0:
            print(
                f"Progress: {number}/{len(selected)}; "
                f"generated={generated}; errors={len(errors)}"
            )

    report = {
        "voice": VOICE,
        "rate": RATE,
        "shard": SHARD,
        "shards": SHARDS,
        "input_records": len(data),
        "selected": len(selected),
        "generated": generated,
        "errors": errors,
    }

    (OUTPUT_DIR / f"manifest-shard-{SHARD}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
