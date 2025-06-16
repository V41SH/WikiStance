import requests, json, time
from urllib.parse import quote
from tqdm import tqdm

USER_AGENT = "MyWikipediaBot/1.0 (me@example.com)"
HEADERS = {"User-Agent": USER_AGENT}
REST_BASE = "https://en.wikipedia.org/api/rest_v1"
API_BASE = "https://en.wikipedia.org/w/api.php"

def fetch_all_revisions_html(
    title: str,
    outfile: str = "portal_current_events_revisions.json",
    pause: float = 0.25,
):
    """
    Retrieve every revision of `title` (HTML) and save to `outfile`.
    Results are ordered from oldest to newest.

    Requires the globals:
        HEADERS, API_BASE, REST_BASE  (already in your script)
    """
    # --- 1. Collect all revision ids + timestamps -------------------------
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvlimit": "max",
        "rvprop": "ids|timestamp",
        "rvdir": "newer",
    }

    revs: list[dict] = []
    cont_token = {}

    def generator():
        while True:
            yield

    for _ in tqdm(generator()):
        resp = requests.get(API_BASE, headers=HEADERS, params={**params, **cont_token}, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        page = next(iter(data["query"]["pages"].values()))
        revs.extend(
            {"rev_id": r["revid"], "timestamp": r["timestamp"]}
            for r in page.get("revisions", [])
        )

        if "continue" not in data:
            break
        cont_token = data["continue"]

    # --- 2. Pull rendered HTML for each revision --------------------------
    encoded_title = quote(title, safe="")
    output: list[dict] = []

    for item in tqdm(revs):
        rev_id = item["rev_id"]
        html_url = f"{REST_BASE}/page/html/{encoded_title}/{rev_id}"
        html_resp = requests.get(html_url, headers=HEADERS, timeout=15)
        html_resp.raise_for_status()

        output.append(
            {
                "rev_id": rev_id,
                "timestamp": item["timestamp"],
                "html": html_resp.text,
            }
        )

        # time.sleep(pause)  # be polite to Wikipedia

    # --- 3. Write to file --------------------------------------------------
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(output)} revisions to {outfile}")

if __name__ == "__main__":
    fetch_all_revisions_html("Portal:Current events")