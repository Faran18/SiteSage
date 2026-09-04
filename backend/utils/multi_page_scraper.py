# backend/utils/multi_page_scraper.py

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from backend.utils.playwright_scraper import extract_text_from_html
import time
import os
import psutil


def _log_memory(label: str):
    """Print current process RAM usage (RSS) in MB, with a short label."""
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / (1024 * 1024)
    print(f"🧠 RAM usage [{label}]: {mem_mb:.1f} MB")


def is_same_domain(url1, url2):
    """Check if two URLs are from the same domain"""
    return urlparse(url1).netloc == urlparse(url2).netloc


def is_in_scope(url: str, root_prefix: str) -> bool:
    """
    True if `url`'s path is the root page itself, a pagination variant of it
    (?page=2 etc.), OR a subcategory nested under it (e.g. root '/pagination'
    matches '/pagination/BMW', '/pagination/Porsche', ...).

    Uses a '/' boundary check so '/pagination' does NOT match an unrelated
    sibling path like '/pagination-archive'.
    """
    path = urlparse(url).path.rstrip('/')
    root = root_prefix.rstrip('/')
    return path == root or path.startswith(root + '/')


def scrape_multiple_pages(start_url: str, max_pages: int = 20, 
                          css_selector: str = None, xpath: str = None):
    """
    Crawl multiple pages starting from a URL.
    
    Returns:
        dict: {
            'pages': [
                {'url': '...', 'text': '...', 'title': '...'},
                ...
            ],
            'total_pages': int,
            'total_chars': int
        }
    """
    
    visited_urls = set()
    failed_urls = set()   # URLs that already errored out — never re-queue these
    to_visit = [start_url]
    pages_data = []
    root_prefix = urlparse(start_url).path

    _log_memory("before browser launch")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"])
        page = browser.new_page()

        _log_memory("after browser launch")
        
        # Block resources
        page.route("**/*", lambda route: route.abort()
                   if route.request.resource_type in ["stylesheet", "font", "image", "media"]
                   else route.continue_())
        
        while to_visit and len(visited_urls) < max_pages:
            current_url = to_visit.pop(0)
            
            # Skip if already visited or already failed once
            if current_url in visited_urls or current_url in failed_urls:
                continue
            
            # Skip if different domain
            if not is_same_domain(current_url, start_url):
                continue
            
            try:
                print(f"🔍 Scraping ({len(visited_urls) + 1}/{max_pages}): {current_url}")
                
                page.goto(current_url, timeout=100000, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                
                html_content = page.content()
                
                # Extract text
                text = extract_text_from_html(html_content, css_selector, xpath)
                
                # Get page title
                title = page.title()
                
                if text and len(text) > 100:  # Only save pages with substantial content
                    pages_data.append({
                        'url': current_url,
                        'text': text,
                        'title': title,
                        'char_count': len(text)
                    })
                
                visited_urls.add(current_url)

                _log_memory(f"after page {len(visited_urls)} ({current_url})")
                
                soup = BeautifulSoup(html_content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    absolute_url = urljoin(current_url, href)
                    
                    if (absolute_url not in visited_urls and 
                        absolute_url not in failed_urls and
                        absolute_url not in to_visit and
                        is_same_domain(absolute_url, start_url) and
                        is_in_scope(absolute_url, root_prefix) and
                        not absolute_url.endswith(('.pdf', '.jpg', '.png', '.zip'))):
                        to_visit.append(absolute_url)
                
                time.sleep(0.5)  
                
            except Exception as e:
                print(f"⚠️ Error scraping {current_url}: {e}")
                failed_urls.add(current_url)   # never retry this URL again
                _log_memory(f"after error on {current_url}")
                continue
        
        browser.close()
        _log_memory("after browser close")
    
    total_chars = sum(p['char_count'] for p in pages_data)

    _log_memory("end of scrape_multiple_pages")
    
    return {
        'pages': pages_data,
        'total_pages': len(pages_data),
        'total_chars': total_chars
    }