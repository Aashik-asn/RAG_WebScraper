import requests, time, re, urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from collections import deque
from tqdm import tqdm

def is_same_domain(a, b):
    return urlparse(a).netloc == urlparse(b).netloc

def clean_text(s):
    return ' '.join(s.split())

def fetch_text(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout, headers={'User-Agent':'rag-bot/1.0'})
        if 'text/html' in r.headers.get('Content-Type',''):
            soup = BeautifulSoup(r.text, 'html.parser')
            for script in soup(['script','style','noscript']):
                script.decompose()
            texts = soup.get_text(separator=' ')
            return clean_text(texts)
        else:
            return ''
    except Exception as e:
        return ''

def extract_links(base, html):
    soup = BeautifulSoup(html, 'html.parser')
    out = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        joined = urljoin(base, href)
        if is_same_domain(base, joined):
            # strip fragments
            u = joined.split('#')[0]
            out.add(u)
    return out

def crawler_ingest(start_url, max_pages=50, max_depth=2):
    '''Crawl same-domain links up to max_pages and max_depth and return list of dicts {url, text}.'''
    q = deque()
    q.append((start_url, 0))
    seen = set([start_url])
    results = []
    while q and len(results) < max_pages:
        url, depth = q.popleft()
        try:
            r = requests.get(url, timeout=10, headers={'User-Agent':'rag-bot/1.0'})
        except Exception:
            continue
        if 'text/html' not in r.headers.get('Content-Type',''):
            continue
        text = ''
        try:
            soup = BeautifulSoup(r.text, 'html.parser')
            for script in soup(['script','style','noscript']):
                script.decompose()
            text = clean_text(soup.get_text(separator=' '))
        except Exception:
            text = ''
        results.append({'url': url, 'text': text})
        if depth < max_depth:
            links = extract_links(url, r.text)
            for l in links:
                if l not in seen:
                    seen.add(l)
                    q.append((l, depth+1))
        # be polite
        time.sleep(0.2)
    return results
