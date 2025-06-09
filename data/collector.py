import requests
import json
from urllib.parse import quote
import time
from torch.nn import Threshold
from links import get_backlinks, get_hyperlinks
from urllib.parse import unquote, quote
from relevance import similarity, embed_batch
from tqdm import tqdm

THRESHOLD = 0.8
LIMIT = 10_000
DEPTH = 3


USER_AGENT = "MyWikipediaBot/1.0 (me@example.com)"
HEADERS = {"User-Agent": USER_AGENT}
REST_BASE = "https://en.wikipedia.org/api/rest_v1"
API_BASE = "https://en.wikipedia.org/w/api.php"

TARGET_PAGES = [
    "2020 United States presidential election",
    "Donald Trump",
    "Joe Biden",
    "Kamala Harris",
    "Mike Pence",
    "2020 Republican Party presidential primaries",
    "2020 Democratic Party presidential primaries",
    "United States presidential debates, 2020",
    "2020 Republican National Convention",
    "2020 Democratic National Convention",
    "Donald Trump 2020 presidential campaign",
    "Joe Biden 2020 presidential campaign",
    "Opinion polling for the 2020 United States presidential election",
    "Russian interference in the 2020 United States elections",
    "Impact of the COVID-19 pandemic on the 2020 United States presidential election",
    "Postal voting in the 2020 United States elections",
    "Endorsements in the 2020 United States presidential election",
    "Timeline of the 2020 United States presidential election",
    "Political positions of Joe Biden",
    "Political positions of Donald Trump"
]

def fetch_page_data(title: str):
    # Decode first in case it's already encoded, then encode properly
    clean_title = unquote(title)
    encoded_title = quote(clean_title, safe='')
    url = f"{REST_BASE}/page/summary/{encoded_title}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "title": data.get("title", title),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "first_paragraph": data.get("extract", "No intro found.")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching summary for {title}: {e}")
        return None

# with mediawiki API
def fetch_page_data_mw(title: str):
    clean_title = unquote(title)
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|info",
        "exintro": True,
        "explaintext": True,
        "titles": clean_title,
        "inprop": "url",
    }

    try:
        response = requests.get(API_BASE, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        try:
            page = next(iter(pages.values()))  # Get the first (and only) page object
            return {
                "title": page.get("title", title),
                "url": page.get("fullurl", ""),
                "first_paragraph": page.get("extract", "No intro found.")
            }
        except:
            print(f"[DEBUG] Pages received for title '{title}': {pages}")
            return {
                "title": " ",
                "url": " ",
                "first_paragraph": " "
            }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching summary for {title}: {e}")
        return {
            "title": " ",
            "url": " ",
            "first_paragraph": " "
        }

def scrape_wikipedia(target_pages):
    
    results = {}
    for page_title in target_pages:
        print(f"Processing: {page_title}")

        first_para = fetch_page_data_mw(page_title)['first_paragraph']
        target_embedding = embed_batch([page_title], [first_para])[0]

        page_data = fetch_page_data_mw(page_title) 
        if not page_data:
            continue
        
        # Get linked pages (outgoing)
        linked_titles = get_hyperlinks(page_title, limit=LIMIT)
        print(f'Got {len(linked_titles)} hyperlinks for {page_title}')
        linked_pages = []
        for title in tqdm(linked_titles):
            page_info = fetch_page_data_mw(title)
            
            if page_info:
                page_embedding = embed_batch([title], [page_info["first_paragraph"]])[0]
    
                # check relevance, skip if below threshold
                if similarity(page_embedding, target_embedding) < THRESHOLD :
                    continue
                else:
                    linked_pages.append(page_info)
        
        page_data["linked_pages"] = linked_pages

        # Get backlinks (incoming)
        backlink_titles = get_backlinks(page_title, limit=LIMIT)
        print(f'Got {len(backlink_titles)} backlinks for {page_title}')
        backlink_pages = []
        for title in tqdm(backlink_titles):
            page_info = fetch_page_data_mw(title)
            if page_info:
                page_embedding = embed_batch([title], [page_info["first_paragraph"]])[0]
    
                # check relevance, skip if below threshold
                if similarity(page_embedding, target_embedding) < THRESHOLD :
                    continue
                else:
                    backlink_pages.append(page_info)
        
        page_data["what_links_here"] = backlink_pages

        results[page_title] = page_data

    save_to_json(results)


def save_to_json(results):
    all_pages = {}
    all_links = []

    for source_title, data in results.items():
        all_pages[source_title] = {
            "title": data["title"],
            "url": data["url"],
            "first_paragraph": data["first_paragraph"]
        }

        for linked in data.get("linked_pages", []):
            linked_title = linked["title"]
            all_pages[linked_title] = linked
            all_links.append({
                "source_title": source_title,
                "target_title": linked_title,
                "link_type": "linked"
            })

        for backlink in data.get("what_links_here", []):
            backlink_title = backlink["title"]
            all_pages[backlink_title] = backlink
            all_links.append({
                "source_title": backlink_title,
                "target_title": source_title,
                "link_type": "backlink"
            })

    with open("pages.json", "w", encoding="utf-8") as f:
        json.dump(list(all_pages.values()), f, indent=2, ensure_ascii=False)

    with open("links.json", "w", encoding="utf-8") as f:
        json.dump(all_links, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # scrape_wikipedia()
    scraped: set[str] = set()  # everything we have already processed
    frontier: list[str] = TARGET_PAGES[:]  # pages to process in this layer

    for _ in range(DEPTH):
        if not frontier:
            print("nothing left to expand, quitting")
            break  # nothing left to expand

        scrape_wikipedia(frontier)  # ← uses the modified signature
        scraped.update(frontier)

        # collect titles just written to pages.json
        with open("pages.json", encoding="utf-8") as f:
            current_titles = {p["title"] for p in json.load(f)}

        # new nodes = pages we just discovered minus everything we have seen
        frontier = list(current_titles - scraped)