# backend/utils/playwright_scraper.py

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrape_website(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.route("**/*", lambda route: route.abort()
                   if route.request.resource_type in ["stylesheet", "font", "image", "media"]
                   else route.continue_())
        
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Scroll to bottom repeatedly until page height stops growing
        prev_height = 0
        for _ in range(20):  # safety cap
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(800)
            prev_height = curr_height

        content = page.content()
        browser.close()
    return content


def extract_text_from_html(html_content: str, css_selector: str = None, xpath: str = None):
    """Extract text with MINIMAL cleaning to preserve content"""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Step 1: Remove only truly useless tags
    unwanted_tags = ["script", "style", "noscript", "iframe"]
    for tag in unwanted_tags:
        for el in soup.find_all(tag):
            el.decompose()
    
    # Step 2: If user provided selector, use it
    if css_selector:
        elements = soup.select(css_selector)
        if elements:
            text = "\n\n".join(el.get_text(strip=True, separator="\n") for el in elements)
            return clean_text_minimal(text)
    
    if xpath:
        from lxml import html
        tree = html.fromstring(str(soup))
        elements = tree.xpath(xpath)
        if elements:
            text = "\n\n".join(el.text_content().strip() for el in elements)
            return clean_text_minimal(text)
    
    # Step 3: Try to find main content area
    main_content = find_main_content(soup)
    if main_content:
        text = main_content.get_text(strip=True, separator="\n")
        return clean_text_minimal(text)
    
    # Step 4: Fallback - get body text
    body = soup.find('body')
    if body:
        text = body.get_text(separator="\n", strip=True)
        return clean_text_minimal(text)
    
    # Last resort
    text = soup.get_text(separator="\n", strip=True)
    return clean_text_minimal(text)


def find_main_content(soup):
    """Try to find the main content area"""
    
    # Priority selectors
    main_selectors = [
        "main",
        "article",
        "[role='main']",
        ".main-content",
        "#main-content",
        ".content",
        "#content"
    ]
    
    for selector in main_selectors:
        elements = soup.select(selector)
        if elements:
            best = max(elements, key=lambda e: len(e.get_text(strip=True)))
            if len(best.get_text(strip=True)) > 200:
                return best
    
    return None


def clean_text_minimal(text: str) -> str:
    """
    MINIMAL cleaning - only remove obvious noise
    """
    if not text:
        return ""
    
    lines = text.split("\n")
    cleaned = []
    
    # Only skip VERY obvious noise
    skip_patterns = [
        "skip to content",
        "skip to main",
        "accept cookies",
        "cookie policy"
    ]
    
    prev = ""
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip obvious noise (case-insensitive, exact match)
        if any(pattern in line.lower() for pattern in skip_patterns):
            continue
        
        # Skip duplicate consecutive lines
        if line == prev:
            continue
        
        cleaned.append(line)
        prev = line
    
    result = "\n".join(cleaned)
    
    # Remove excessive blank lines
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    
    return result.strip()