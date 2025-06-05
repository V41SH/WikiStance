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
    "2020 United States presidential election",
    "Donald Trump",
    "Joe Biden",
    "Kamala Harris",
    "Mike Pence"
]


def fetch_summary(title):
    # Decode once in case it's double-encoded
    clean_title = unquote(title)
    encoded_title = quote(clean_title, safe='')
    
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("extract", "")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching summary for {title}: {e}")
        return None


def fetch_page_data(title):
    """Fetch title, URL, and first paragraph (REST API)."""
    url = f"{REST_BASE}/page/summary/{quote(title)}"
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

def fetch_links_legacy(title, link_type="links"):
    """Fetch links or backlinks (Legacy API)."""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "links" if link_type == "links" else "linkshere",
        "pllimit": 50  # Limit to 50 links
    }
    try:
        response = requests.get(LEGACY_BASE, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        return [link["title"] for page in pages.values() for link in page.get(link_type, [])]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {link_type} for {title}: {e}")
        return []

def scrape_wikipedia():
    results = {}
    for page_title in TARGET_PAGES:
        print(f"Processing: {page_title}")
        page_data = fetch_summary(page_title)
        if not page_data:
            continue
        
        # Get linked pages (outgoing)
        linked_titles = get_hyperlinks(page_title)
        page_data["linked_pages"] = [
            fetch_summary(title) for title in linked_titles if fetch_summary(title)
        ]

        # Get "What Links Here" (incoming)
        backlink_titles = get_backlinks(page_title)
        page_data["what_links_here"] = [
            fetch_summary(title) for title in backlink_titles if fetch_summary(title)
        ]

        results[page_title] = page_data

    # Save to JSON
    with open("wikipedia_final_data.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Data saved to 'wikipedia_final_data.json'.")

if __name__ == "__main__":
    scrape_wikipedia()