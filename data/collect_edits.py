import json
import threading
import math
from edit import main
import os
# load your pages
with open("pages.json", "r", encoding="utf-8") as f:
    pages = json.load(f)

# compute chunk size & slice into 3 parts
n = len(pages)
chunk_size = math.ceil(n / 40)
chunks = [
    pages[i : i + chunk_size]
    for i in range(0, n, chunk_size)
]

def worker(pages_chunk):
    for item in pages_chunk:
        fn = f"edits_{item['title']}.json"
        if os.path.exists(fn):
            continue
        main(
            title=item["title"],
            start_ts="2021-09-01T23:50:00Z",
            end_ts="2021-11-01T04:02:00Z",
            limit=20000
        )

threads = []
for chunk in chunks:
    t = threading.Thread(target=worker, args=(chunk,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
