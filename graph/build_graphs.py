import os
import json
import re
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime

DATA_DIR = '../data/edits/' 
DELTA_DAYS = 2
IMPLICIT_SIM_THRESHOLD = 0.3
BURST_THRESHOLD_PERCENTILE = 90
WIKI_LINK_RE = re.compile(r'\[\[(.*?)\]\]')

# -----------------------
# Helpers
# -----------------------

def parse_entity_links(json_path):
    with open(json_path, 'r') as f:
        edits = json.load(f)

    entity = os.path.splitext(os.path.basename(json_path))[0][6:]
    results = []

    for edit in edits:
        ts = datetime.fromisoformat(edit["timestamp"].replace("Z", "+00:00"))
        added_text = ' '.join(edit.get("added", []))
        links = WIKI_LINK_RE.findall(added_text)
        clean_links = [l.split('|')[0].strip() for l in links]
        results.append({
            "entity": entity,
            "timestamp": ts,
            "added": edit.get("added", []),
            "links_added": set(clean_links)
        })

    return results

def build_all_edits(data_dir):
    all_edits = []
    for fname in os.listdir(data_dir):
        if fname.endswith(".json"):
            path = os.path.join(data_dir, fname)
            all_edits.extend(parse_entity_links(path))
    return all_edits

# -----------------------
# Explicit Graph
# -----------------------

def build_explicit_graph(all_edits, delta_days=2):
    graph = defaultdict(set)
    links_by_entity = defaultdict(list)

    for edit in all_edits:
        links_by_entity[edit["entity"]].append(edit)

    for edits in links_by_entity.values():
        edits.sort(key=lambda x: x["timestamp"])

    for e1, e1_edits in links_by_entity.items():
        for e1_edit in e1_edits:
            ts1 = e1_edit["timestamp"]
            for e2 in e1_edit["links_added"]:
                if e2 not in links_by_entity:
                    continue
                for e2_edit in links_by_entity[e2]:
                    ts2 = e2_edit["timestamp"]
                    if abs((ts2 - ts1).days) <= delta_days and e1 in e2_edit["links_added"]:
                        graph[e1].add(e2)
                        graph[e2].add(e1)
    return graph

# -----------------------
# Implicit Graph
# -----------------------

def detect_bursts(edits, threshold_percentile=90):
    daily_counts = Counter()
    for e in edits:
        day = e['timestamp'].date()
        daily_counts[day] += 1

    if not daily_counts:
        return set()

    counts = list(daily_counts.values())
    threshold = np.percentile(counts, threshold_percentile)
    burst_days = {day for day, count in daily_counts.items() if count >= threshold}
    return burst_days

def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0
    return len(set1 & set2) / len(set1 | set2)

def build_implicit_graph(all_edits, burst_map, similarity_threshold=0.3):
    graph = defaultdict(set)
    edits_by_entity = defaultdict(list)

    for e in all_edits:
        edits_by_entity[e['entity']].append(e)

    entities = list(edits_by_entity.keys())

    for i, e1 in enumerate(entities):
        for e2 in entities[i+1:]:
            shared_burst_days = burst_map[e1] & burst_map[e2]
            if not shared_burst_days:
                continue

            max_sim = 0
            for day in shared_burst_days:
                a1 = set()
                a2 = set()
                for e in edits_by_entity[e1]:
                    if e['timestamp'].date() == day:
                        a1.update(' '.join(e.get('added', [])).split())
                for e in edits_by_entity[e2]:
                    if e['timestamp'].date() == day:
                        a2.update(' '.join(e.get('added', [])).split())

                sim = jaccard_similarity(a1, a2)
                max_sim = max(max_sim, sim)

            if max_sim >= similarity_threshold:
                graph[e1].add(e2)
                graph[e2].add(e1)

    return graph


if __name__ == "__main__":
    print(f"Reading edit data from {DATA_DIR}")
    all_edits = build_all_edits(DATA_DIR)
    print(f"Loaded {len(all_edits)} total edits.")

    print("\n Building Explicit Graph...")
    explicit_graph = build_explicit_graph(all_edits, DELTA_DAYS)
    print(f"Explicit Graph has {len(explicit_graph)} entities with edges.")
    for node, edges in explicit_graph.items():
        print(f"  {node}: {list(edges)}")

    print("\n Detecting bursts...")
    edits_by_entity = defaultdict(list)
    for e in all_edits:
        edits_by_entity[e['entity']].append(e)

    burst_map = {entity: detect_bursts(edits, BURST_THRESHOLD_PERCENTILE)
                    for entity, edits in edits_by_entity.items()}
    
    print("➡ Building Implicit Graph...")
    implicit_graph = build_implicit_graph(all_edits, burst_map, IMPLICIT_SIM_THRESHOLD)
    print(f"Implicit Graph has {len(implicit_graph)} entities with edges.")
    for node, edges in implicit_graph.items():
        print(f"  {node}: {list(edges)}")
