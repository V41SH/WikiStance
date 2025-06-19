import json
from pathlib import Path

src_dir = Path("riots")          # adjust to the directory with the JSON files
out_file = "riots.json"

combined = []
for fp in src_dir.glob("*.json"):
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        continue                       # skip malformed files
    if isinstance(data, list) and data:  # ignore empty “[]” files
        combined.extend(data)

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)
