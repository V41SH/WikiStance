import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import wikipediaapi
from typing import List
import random

def get_backlinks(title: str, limit: int=1000) -> List:
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "list": "backlinks",
        "bltitle": title,
        "blnamespace": 0,
        "bllimit": 500,
    }

    backlinks = []
    while True:
        response = S.get(url=URL, params=params).json()
        for link in response["query"]["backlinks"]:
            backlinks.append(link["title"])
        if "continue" in response:
            params.update(response["continue"])
        else:
            break
    
    backlinks = [i.split('/')[-1] for i in backlinks]
    return random.sample(backlinks, limit) # get 1000 links randomly


def get_hyperlinks(article_title: str, limit: int=1000) -> List:
    url = f"https://en.wikipedia.org/wiki/{article_title}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    base_url = "https://en.wikipedia.org"
    links = set()

    for a in soup.select("div.mw-parser-output a[href^='/wiki/']"):
        href = a.get('href')
        if ':' not in href:  # Skip special namespaces like File:, Help:, etc.
            full_url = urljoin(base_url, href)
            links.add(full_url)

    links = [i.split('/')[-1] for i in links]
    return random.sample(sorted(links), limit) # get 1000 links randomly

def get_article_hyperlinks(article_title):
    wiki_wiki = wikipediaapi.Wikipedia(user_agent='my-agent',language='en')
    page = wiki_wiki.page(article_title)
    return page.links

def get_article_backlinks(article_title):
    wiki_wiki = wikipediaapi.Wikipedia(user_agent='my-agent',language='en')
    page = wiki_wiki.page(article_title)
    
    # backlinks() returns dict of {page_name: page_object}
    backlinks = page.backlinks
    return [title for title in backlinks]  # just return the titles

if __name__ == '__main__':
    back = get_backlinks('2020 United States presidential election')
    print(len(back))