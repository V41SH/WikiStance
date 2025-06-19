import json
import requests
import difflib
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone

USER_AGENT = "MyWikipediaBot/1.0 (me@example.com)"
HEADERS     = {"User-Agent": USER_AGENT}
API_BASE    = "https://en.wikipedia.org/w/api.php"

###############################################################################
# helpers
###############################################################################

def _query(params: dict) -> dict:
    r = requests.get(API_BASE, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def _get_two_revisions(title: str, ts_iso: str):
    """Return the newest revision ≤ ts and its direct parent."""
    params = {
        "action":  "query",
        "format":  "json",
        "prop":    "revisions",
        "titles":  title,
        "rvstart": ts_iso,      # start searching at the timestamp
        "rvdir":   "older",     # walk backwards in time
        "rvlimit": 2,           # current + parent
        "rvprop":  "ids|timestamp|slots|content",
        "rvslots": "main",
    }
    pages = _query(params)["query"]["pages"]
    revs  = next(iter(pages.values())).get("revisions", [])
    if len(revs) < 2:
        return None, None
    return revs[0], revs[1]          # newest ≤ ts, then its parent

def _unified_diff(old: str, new: str, ctx: int = 3) -> str:
    lines = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        lineterm="",
        n=ctx
    )
    return "\n".join(lines)

def _snippet_ctx(text: str, snippet: str, win: int = 250) -> str | None:
    idx = text.find(snippet)
    if idx == -1:
        return None
    lo  = max(0, idx - win)
    hi  = min(len(text), idx + len(snippet) + win)
    return text[lo:hi]

###############################################################################
# main routine
###############################################################################

def enrich_events(path_in: str | Path,
                  # path_out: str | Path,
                  ctx_lines: int = 3,
                  snippet_win: int = 250) -> None:
    events   = json.loads(Path(path_in).read_text(encoding="utf-8"))
    enriched = []

    for ev in events:
        title = ev["entity"]
        ts    = ev["timestamp"]          # ISO-8601 coming from your JSON
        new, old = _get_two_revisions(title, ts)
        if not new:
            continue                     # nothing to compare – skip

        new_txt = new["slots"]["main"]["*"]
        old_txt = old["slots"]["main"]["*"]

        diff_txt   = _unified_diff(old_txt, new_txt, ctx_lines)
        snippet_ct = _snippet_ctx(new_txt, ev["text"], snippet_win)

        enriched.append({
            "entity":          title,
            "event_timestamp": ts,
            "rev_id":          new["revid"],
            "parent_rev_id":   old["revid"],
            "diff":            diff_txt,
            "snippet_context": snippet_ct,
        })

    # Path(path_out).write_text(json.dumps(enriched, indent=2, ensure_ascii=False),
    #                           encoding="utf-8")
    return enriched

###############################################################################
# usage
###############################################################################

if __name__ == "__main__":
    # enrich_events("../../outputs/riots/event_0.json", "events_enriched.json", ctx_lines=3, snippet_win=250)
    IN_DIR = Path("../../outputs/election")  # folder with event_*.json
    OUT_PATH = "election.json"  # merged file

    merged = []
    for fp in sorted(IN_DIR.glob("event_*.json")):  # event_0.json … event_N.json
        event_id = int(fp.stem.split("_")[1])  # 0, 1, 2, …
        with fp.open(encoding="utf-8") as f:
            merged.append({
                "event_id": event_id,
                # "edits": json.load(f)  # all data from that event file
                "edits": enrich_events(fp, ctx_lines=15, snippet_win=500)  # all data from that event file
            })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

