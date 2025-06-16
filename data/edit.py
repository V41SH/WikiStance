import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import math
import re
import json
def get_revisions(title, start_ts=None, end_ts=None, limit=500):
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"

    PARAMS = {
        "action":  "query",
        "prop":    "revisions",
        "titles":  title,
        "rvprop":  "ids|timestamp|comment|tags",
        "rvlimit": limit,
        "rvdir":   "older",
        "format":  "json"
    }
    if start_ts:
        print("start", start_ts)
        PARAMS["rvstart"] = end_ts
    if end_ts:
        print("end", end_ts)
        PARAMS["rvend"]   = start_ts
    R = S.get(URL, params=PARAMS)
    data = R.json()["query"]["pages"]
    page = next(iter(data.values()))
    return page.get("revisions", [])


def bucket_revisions_by_delta(revisions, delta_minutes):
    # parse timestamps
    rev_times = [
        (datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")), r["revid"])
        for r in revisions
    ]
    if not rev_times:
        return []

    rev_times.sort()  # oldest → newest
    window_start = rev_times[0][0]
    window_end = rev_times[-1][0]
    delta = timedelta(minutes=delta_minutes)

    # how many buckets?
    span = window_end - window_start
    n_buckets = math.ceil(span / delta) or 1

    # initialize empty buckets
    buckets = [[] for _ in range(n_buckets)]

    # assign each revision to its bucket index
    for ts, revid in rev_times:
        idx = int((ts - window_start) / delta)
        if idx >= n_buckets:
            idx = n_buckets - 1
        buckets[idx].append((ts, revid))
    print(len(buckets))
    return [
        (window_start + i * delta, bucket)
        for i, bucket in enumerate(buckets)
    ]

def get_textual_changes(from_rev, to_rev):
    URL = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "compare",
        "fromrev": from_rev,
        "torev": to_rev,
        "format": "json"
    }
    r = requests.get(URL, params=params).json()
    # print(r)
    try:
        cmp = r["compare"]
    except:
        print("ecountered error in processing")
        return {"added": [], "deleted": []}

    if "reverted" in cmp:
        # this diff was a revert — skip it
        return None
    html = cmp["*"]
    # print(html)
    soup = BeautifulSoup(html, "html.parser")
    added_raw = [td.get_text(strip=True) for td in soup.select(".diff-addedline")]
    deleted_raw = [td.get_text(strip=True) for td in soup.select(".diff-deletedline")]

    def is_textual(line):
        return not re.search(
        r'\.(jpg|jpeg|png|svg|gif)'
        r'|^\|\s*(image|alt|caption|bgcolor|title|logo)\s*='
        r'|\[\[(File|Image):',
        line,
        re.IGNORECASE
    )

    added = [line for line in added_raw if is_textual(line)]
    deleted = [line for line in deleted_raw if is_textual(line)]

    if not added and not deleted:
        return None
    return {"added": added, "deleted": deleted}
def is_revert(prev_changes, curr_changes):
    # both must be non-None, and curr adds == prev deletes, curr deletes == prev adds
    return (
        prev_changes is not None
        and curr_changes is not None
        and curr_changes["added"]   == prev_changes["deleted"]
        and curr_changes["deleted"] == prev_changes["added"]
    )

def jaccard(edit_a, edit_b):
    """
    Compute Jaccard similarity between two edits, where each edit is a list of strings.
    Tokenization is done on “words” (alphanumeric sequences).
    """
    # extract word‐tokens (lowercased) from each edit
    tokens_a = set(
        w.lower()
        for line in edit_a
        for w in re.findall(r'\w+', line)
    )
    tokens_b = set(
        w.lower()
        for line in edit_b
        for w in re.findall(r'\w+', line)
    )

    # corner case: both empty → identical
    if not tokens_a and not tokens_b:
        print("NONE")
        return 1.0

    # standard Jaccard: |A ∩ B| / |A ∪ B|
    intersection = tokens_a & tokens_b
    union        = tokens_a | tokens_b
    print(len(intersection) / len(union))
    return len(intersection) / len(union)

def main(title, start_ts, end_ts, limit, delta=60):
    results = []
    # 1) fetch all revisions in the time frame
    revisions = get_revisions(title, limit=limit, start_ts=start_ts, end_ts=end_ts)
    # 2) bucket them
    buckets = bucket_revisions_by_delta(revisions, delta)
    for window_start, bucket in buckets:
        if not bucket:
            continue  # no edits in this interval
        print(f"\n=== Window starting {window_start.isoformat()} (+{delta}m) ===")

        prev_changes = {"added": " ", "deleted":" "}
        for i, (ts, rev) in enumerate(bucket[:-1]):
            _, next_rev = bucket[i + 1]
            curr_changes = get_textual_changes(rev, next_rev)
            # print(curr_changes.values())
            if curr_changes:
                sim_added = jaccard(curr_changes["added"], prev_changes["deleted"])
                sim_deleted = jaccard(curr_changes["deleted"], prev_changes["added"])
                # if not curr_changes.values():
                #     prev_changes = " "
                #     continue
                # print(jaccard(curr_changes, prev_changes))
                if (sim_added > 0.8):
                    curr_changes["added"] = []
                elif sim_deleted > 0.8:
                    curr_changes["deleted"] = []
                else:
                    continue
                results.append({
                    "title": title,
                    "timestamp": ts.isoformat(),
                    "added": curr_changes["added"],
                    "deleted": curr_changes["deleted"]
                })
                prev_changes = curr_changes

        time.sleep(0.5)
    with open(f"edits_{title}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
#YYYY-MM-DDThh:mm:ssZ
# main("Joe Biden", start_ts=None, end_ts=None, limit=200)
# with open("pages.json", "r", encoding="utf-8") as f:
#     data = json.load(f)
#
#     for item in data:
#         main(title=item["title"], end_ts="2025-12-03T04:02:00Z", start_ts="2020-11-03T23:50:00Z", limit=2000)
