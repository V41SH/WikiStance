# import json

# # load the input array of objects
# with open("links.json", encoding="utf-8") as f:
#     rows = json.load(f)

# seen, deduped = set(), []
# for obj in rows:
#     key = obj["url"]               # change to ("title", obj["url"]) or json.dumps(obj, sort_keys=True) if you need a different notion of “duplicate”
#     if key not in seen:
#         seen.add(key)
#         deduped.append(obj)

# with open("dataset_dedup.json", "w", encoding="utf-8") as f:
#     json.dump(deduped, f, ensure_ascii=False, indent=2)


import json

with open("links.json", encoding="utf-8") as f:
    links = json.load(f)

seen, deduped = set(), []
for link in links:
    # Treat links as duplicates when source & target are the same.
    # If you also want to consider link_type, include it in the tuple.
    key = (link["source_title"], link["target_title"])
    if key not in seen:
        seen.add(key)
        deduped.append(link)

with open("links_dedup.json", "w", encoding="utf-8") as f:
    json.dump(deduped, f, ensure_ascii=False, indent=2)
