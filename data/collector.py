import requests
import json
from urllib.parse import quote
import time
from links import get_backlinks, get_hyperlinks
from urllib.parse import unquote, quote
from relevance import similarity, embedding

USER_AGENT = "MyWikipediaBot/1.0 (me@example.com)"
HEADERS = {"User-Agent": USER_AGENT}
REST_BASE = "https://en.wikipedia.org/api/rest_v1"
API_BASE = "https://en.wikipedia.org/w/api.php"

TARGET_PAGES = [
    "2020 United States presidential election",
    "Donald Trump",
    "Joe Biden",
    "Kamala Harris",
    "Mike Pence"
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
        page = next(iter(pages.values()))  # Get the first (and only) page object

        return {
            "title": page.get("title", title),
            "url": page.get("fullurl", ""),
            "first_paragraph": page.get("extract", "No intro found.")
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching summary for {title}: {e}")
        return None

def scrape_wikipedia():
    
    results = {}
    for page_title in TARGET_PAGES:
        print(f"Processing: {page_title}")

        # get embeddings for target pages
        target_embedding = embedding(fetch_page_data_mw(page_title)['first_paragraph'])
        page_data = fetch_page_data_mw(page_title) 
        if not page_data:
            continue
        
        # Get linked pages (outgoing)
        linked_titles = get_hyperlinks(page_title)
        print(f'Got hyperlinks for {page_title}')
        linked_pages = []
        for title in linked_titles:
            page_info = fetch_page_data_mw(title)
            
            if page_info:
                page_embedding = embedding(page_info['first_paragraph'])
    
                # check relevance, skip if below threshold
                if similarity(page_embedding, target_embedding) < 0.7 :
                    continue
                else:
                    linked_pages.append(page_info)
        
        page_data["linked_pages"] = linked_pages

        # Get backlinks (incoming)
        backlink_titles = get_backlinks(page_title)
        print(f'Got backlinks for {page_title}')
        backlink_pages = []
        for title in backlink_titles:
            page_info = fetch_page_data_mw(title)
            if page_info:
                # print('first para type ', type(page_info['first_paragraph']))
                page_embedding = embedding(page_info['first_paragraph'])
    
                # check relevance, skip if below threshold
                if similarity(page_embedding, target_embedding) < 0.7 :
                    continue
                else:
                    backlink_pages.append(page_info)
        
        page_data["what_links_here"] = backlink_pages

        results[page_title] = page_data

    # Save to JSON
    with open("wikipedia_final_data.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Data saved to 'wikipedia_final_data.json'.")

if __name__ == "__main__":
    
    # start = time.time()
    # print(fetch_page_data_mw('Donald Trump'))
    # end = time.time()
    # print('first', end - start)
    # start = time.time()
    # print(fetch_page_data('Donald Trump'))
    # end = time.time()
    # print('second', end - start)

    scrape_wikipedia()