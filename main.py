
from graph.build_graphs import *
from graph.ECA import entity_cluster_aggregation

from collections import defaultdict
from datetime import datetime
import os
import json

DATA_DIR = "data/debate/"
OUTPUT_DIR = "outputs/debate"
os.makedirs(OUTPUT_DIR, exist_ok=True)
MODE = "implicit"  # or "implicit"
DELTA_DAYS = 2
BURST_PERCENTILE = 90
SIMILARITY_THRESHOLD = 0.3
JACCARD_THRESHOLD = 0.8
MIN_CLUSTER_SIZE = 3


print("🔍 Loading edits...")
all_edits = build_all_edits(DATA_DIR)
print(f"Loaded {len(all_edits)} edits.")

edits_by_date = defaultdict(list)
for e in all_edits:
    day = e['timestamp'].date()
    edits_by_date[day].append(e)

temporal_graphs = {}

if MODE == "explicit":
    for day, edits in edits_by_date.items():
        graph = build_explicit_graph(edits, delta_days=DELTA_DAYS)
        if graph:
            temporal_graphs[str(day)] = graph

elif MODE == "implicit":
    print("📈 Detecting bursts for implicit mode...")
    edits_by_entity = defaultdict(list)
    for e in all_edits:
        edits_by_entity[e['entity']].append(e)
    burst_map = {entity: detect_bursts(edits, BURST_PERCENTILE) for entity, edits in edits_by_entity.items()}

    for day, edits in edits_by_date.items():
        graph = build_implicit_graph(edits, burst_map, SIMILARITY_THRESHOLD)
        if graph:
            temporal_graphs[str(day)] = graph

print(f"Built {len(temporal_graphs)} temporal graphs.")

print("Running Entity Cluster Aggregation...")
events = entity_cluster_aggregation(
    temporal_graphs,
    strategy=MODE,
    gamma=JACCARD_THRESHOLD
)

print(f"\nDetected {len(events)} evolving events:\n")
for idx, event in enumerate(events):
    print(f"🗓️ Event {idx+1}: {event['start']} → {event['end']}")
    print(f"   Entities: {sorted(event['entities'])}\n")

print("Saving event data for inference...")

for event_id, event in enumerate(events):
    start = datetime.strptime(event["start"], "%Y-%m-%d").date()
    end = datetime.strptime(event["end"], "%Y-%m-%d").date()
    entities = event["entities"]

    # Gather all edits matching the event
    event_edits = []
    for edit in all_edits:
        if edit["entity"] in entities:
            # ts = edit["timestamp"].date()
            ts = edit["timestamp"]#.date()
            # print(start, ts, end)
            if start <= ts.date() <= end:
                added_text = ' '.join(edit.get("added", []))
                if added_text.strip():
                    event_edits.append({
                        "text": added_text,
                        "timestamp": str(ts),
                        "entity": edit["entity"],
                        "event_id": event_id
                    })

    # Save to file
    outfile = os.path.join(OUTPUT_DIR, f"event_{event_id}.json")
    with open(outfile, 'w') as f:
        json.dump(event_edits, f, indent=2)

print(f"Exported {len(events)} event files to {OUTPUT_DIR}")