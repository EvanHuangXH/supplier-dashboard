"""Scraper for 方圆定制 (fypod.com) — 8ding platform."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_html, run_scraper

BASE_URL = "https://www.fypod.com"


def extract_categories(html):
    soup = BeautifulSoup(html, "html.parser")
    categories = []
    seen = set()
    for link in soup.select('.my-product-category a'):
        href = link.get('href', '')
        name = link.get_text(strip=True)
        if not href or not name: continue
        if name in seen or '全部' in name: continue
        seen.add(name)
        full_url = href if href.startswith('http') else f'{BASE_URL}{href}'
        categories.append({'name': name, 'url': full_url})
    return categories


def parse_product_card(card, category_name=None):
    name_link = card.select_one(".card-body h3 a")
    if not name_link: return None
    name = name_link.get_text(strip=True)
    href = name_link.get("href", "")
    product_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    price = None
    money_el = card.select_one(".money")
    if money_el:
        try: price = float(money_el.get("data-money", ""))
        except: pass

    image_url = None
    img_el = card.select_one(".card-image img")
    if img_el:
        image_url = img_el.get("data-original") or img_el.get("src")

    is_hot = bool(card.select_one(".badge.badge-warning"))
    small_ps = card.select(".card-body p.small")
    material_tags = []
    delivery_days = None
    for p in small_ps:
        text = p.get_text(strip=True)
        if "材质" in text:
            mat_text = text.split(":", 1)[-1].strip() if ":" in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、]', mat_text) if m.strip()]
        if "时间" in text:
            nums = re.findall(r'(\d+)', text)
            if nums: delivery_days = int(nums[0])

    return {
        "name": name, "description": None, "price": price,
        "price_unit": None, "currency": "CNY", "delivery_days": delivery_days,
        "listed_at": None, "is_hot": is_hot, "category": category_name,
        "material_tags": material_tags, "image_url": image_url,
        "product_url": product_url, "raw": {"supplier": "方圆定制"},
    }


def scrape():
    products = []
    seen_urls = set()
    print("  Extracting categories...")
    try:
        html = fetch_html(f"{BASE_URL}/custom")
        categories = extract_categories(html)
        print(f"  Found {len(categories)} categories")
    except Exception as e:
        print(f"  Failed: {e}")
        categories = []

    to_scrape = [{'name': None, 'url': f'{BASE_URL}/custom?page=1'}] + categories
    for ci, cat in enumerate(to_scrape):
        cat_name = cat['name']
        if ci % 20 == 0:
            print(f"  [{ci+1}/{len(to_scrape)}] {cat_name or '(all)'}", flush=True)

        page = 1
        stale = 0
        while page <= 15:
            url = f"{cat['url']}&page={page}" if '?' in cat['url'] else f"{cat['url']}?page={page}"
            try: html = fetch_html(url)
            except: break
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".card-product")
            if not cards: break

            new_p = 0
            for card in cards:
                product = parse_product_card(card, category_name=cat_name)
                if product and product['product_url'] not in seen_urls:
                    seen_urls.add(product['product_url'])
                    products.append(product)
                    new_p += 1

            if new_p == 0:
                stale += 1
                if stale >= 2: break
            else: stale = 0
            page += 1

    return products


if __name__ == "__main__":
    run_scraper("方圆定制", scrape)
