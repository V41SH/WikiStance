import requests
import json
from urllib.parse import quote
import time
from links import get_backlinks, get_hyperlinks
from urllib.parse import unquote, quote

USER_AGENT = "MyWikipediaBot/1.0 (me@example.com)"
HEADERS = {"User-Agent": USER_AGENT}
REST_BASE = "https://en.wikipedia.org/api/rest_v1"
LEGACY_BASE = "https://en.wikipedia.org/w/api.php"

TARGET_PAGES = [
    'MV_Lazio',
    # "2020 United States presidential election",
    # "Donald Trump",
    # "Joe Biden",
    # "Kamala Harris",
    # "Mike Pence"
]

def fetch_page_data(title):
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

def scrape_wikipedia():
    results = {}
    for page_title in TARGET_PAGES:
        print(f"Processing: {page_title}")
        page_data = fetch_page_data(page_title)  # Changed from fetch_summary to fetch_page_data
        if not page_data:
            continue
        
        # Get linked pages (outgoing)
        linked_titles = get_hyperlinks(page_title)
        linked_pages = []
        for title in linked_titles:
            page_info = fetch_page_data(title)
            if page_info:
                linked_pages.append(page_info)
        page_data["linked_pages"] = linked_pages

        # Get "What Links Here" (incoming)
        backlink_titles = get_backlinks(page_title)
        backlink_pages = []
        for title in backlink_titles:
            page_info = fetch_page_data(title)
            if page_info:
                backlink_pages.append(page_info)
        page_data["what_links_here"] = backlink_pages

        results[page_title] = page_data

    # Save to JSON
    with open("wikipedia_final_data.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Data saved to 'wikipedia_final_data.json'.")

if __name__ == "__main__":
    scrape_wikipedia()