# -*- coding: utf-8 -*-
"""Regenerate only tts_text/status from original_text; never edits original_text or ids.
Usage: python tts/refresh_dataset.py input.json output.json
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import prepare, status

if len(sys.argv) != 3:
    raise SystemExit("Usage: python tts/refresh_dataset.py input.json output.json")
source, target = sys.argv[1:]
with open(source, encoding="utf-8") as f: rows = json.load(f)
if not isinstance(rows, list): raise SystemExit("Expected a JSON list")
seen_ids = set()
for i, row in enumerate(rows):
    if not isinstance(row, dict) or not isinstance(row.get("original_text"), str):
        raise SystemExit(f"Invalid row at index {i}: missing original_text")
    rid = row.get("id")
    if rid in seen_ids: raise SystemExit(f"Duplicate id: {rid}")
    seen_ids.add(rid)
    original = row["original_text"]
    row["tts_text"] = prepare(original)
    row["status"] = status(original, row["tts_text"])
with open(target, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"Updated {len(rows)} records. original_text and id values were preserved.")
