import json
import csv
from pathlib import Path

IN_PATH = Path("debate.json")   # merged events file
OUT_CSV = "debate.csv"

rows = []
with IN_PATH.open(encoding="utf-8") as f:
    for event in json.load(f):
        eid = event["event_id"]
        for edit in event["edits"]:
            rows.append({
                "Tweet":  edit["diff"],
                "Time":   edit["event_timestamp"],
                "Event":  eid,
                "Stance": ""
            })

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Tweet", "Time", "Event", "Stance"])
    writer.writeheader()
    writer.writerows(rows)
