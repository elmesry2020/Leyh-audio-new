# -*- coding: utf-8 -*-
"""Audit project audio text coverage and create a review queue; this does not certify pronunciation."""
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "leyh_texts_refreshed.json"
OUT = ROOT / "tts"
rows = json.loads(DATA.read_text(encoding="utf-8"))
review = [r for r in rows if r.get("status") in {"plain", "review"}]
with (OUT / "pronunciation_review_queue.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "type", "status", "original_text", "tts_text"])
    writer.writeheader()
    for r in review:
        writer.writerow({k: r.get(k, "") for k in writer.fieldnames})

report = {
    "total_records": len(rows),
    "types": dict(Counter(r.get("type", "unknown") for r in rows)),
    "status_counts": dict(Counter(r.get("status", "unknown") for r in rows)),
    "review_queue_records": len(review),
    "warning": (
        "Status is a heuristic, not a pronunciation certification. "
        "Unvocalized Arabic stories require human/native-speaker review or verified tashkeel; "
        "the script does not guess missing vowels."
    ),
}
(OUT / "pronunciation_audit.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
