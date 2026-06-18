"""Scraper for 博亚达 (diybyd.com) — with category extraction from sidebar."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_html, run_scraper

BASE_URL = "https://www.diybyd.com"


def extract_categories(html):
    """Extract category names and URLs from sidebar <ul class='my-product-category'>."""
    soup = BeautifulSoup(html, "html.parser")
    categories = []
    seen = set()
    for link in soup.select('.my-product-category a'):
        href = link.get('href', '')
        name = link.get_text(strip=True)
        if not href or not name:
            continue
        if name in seen or '全部' in name:
            continue
        seen.add(name)
        full_url = href if href.startswith('http') else f'{BASE_URL}{href}'
        categories.append({'name': name, 'url': full_url})
    return categories


def parse_product_card(card, category_name=None):
    """Parse a single .card-product element."""
    # Name + URL from h3 > a
    name_link = card.select_one(".card-body h3 a")
    if not name_link:
        return None

    name = name_link.get_text(strip=True)
    href = name_link.get("href", "")
    product_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    # Price from data-money attribute
    price = None
    money_el = card.select_one(".money")
    if money_el:
        money_str = money_el.get("data-money", "")
        try:
            price = float(money_str)
        except (ValueError, TypeError):
            pass

    # Image from data-original (lazy loaded)
    image_url = None
    img_el = card.select_one(".card-image img")
    if img_el:
        image_url = img_el.get("data-original") or img_el.get("src")

    # Badges
    is_hot = False
    hot_badge = card.select_one(".badge.badge-warning")
    if hot_badge and "hot" in hot_badge.get_text(strip=True).lower():
        is_hot = True

    is_new = False
    new_badge = card.select_one(".badge.badge-success")
    if new_badge and "new" in new_badge.get_text(strip=True).lower():
        is_new = True

    # Product details
    small_ps = card.select(".card-body p.small")
    material_tags = []
    delivery_days = None
    description_parts = []

    for p in small_ps:
        text = p.get_text(strip=True)
        description_parts.append(text)
        if "材质" in text:
            mat_text = text.split(":", 1)[-1].strip() if ":" in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、]', mat_text) if m.strip()]
        if "生产时间" in text or "时间" in text:
            nums = re.findall(r'(\d+)', text)
            if nums:
                delivery_days = int(nums[0])

    description = "; ".join(description_parts) if description_parts else None

    return {
        "name": name,
        "description": description,
        "price": price,
        "price_unit": None,
        "currency": "CNY",
        "delivery_days": delivery_days,
        "listed_at": None,
        "is_hot": is_hot,
        "category": category_name,
        "material_tags": material_tags,
        "image_url": image_url,
        "product_url": product_url,
        "raw": {"supplier": "博亚达", "is_new": is_new},
    }


def scrape():
    """Scrape all products: first get categories, then iterate each."""
    products = []
    seen_urls = set()

    # Phase 1: Get categories from sidebar
    print("  Extracting categories from sidebar...")
    try:
        html = fetch_html(f"{BASE_URL}/custom")
        categories = extract_categories(html)
        print(f"  Found {len(categories)} categories")
    except Exception as e:
        print(f"  Category extraction failed: {e}, falling back to all-products")
        categories = []

    # Always include "all products" as first entry
    to_scrape = [{'name': None, 'url': f'{BASE_URL}/custom?page=1'}] + categories

    for ci, cat in enumerate(to_scrape):
        cat_name = cat['name']
        label = cat_name or '(all)'
        print(f"  [{ci+1}/{len(to_scrape)}] {label}", flush=True)

        page = 1
        cat_stale = 0
        while page <= 5:  # Max 5 pages per category
            if cat_name:
                url = f"{cat['url']}&page={page}" if '?' in cat['url'] else f"{cat['url']}?page={page}"
            else:
                url = f"{BASE_URL}/custom?page={page}"

            try:
                html = fetch_html(url)
            except Exception:
                break

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".card-product")
            if not cards:
                break

            new_on_page = 0
            for card in cards:
                product = parse_product_card(card, category_name=cat_name)
                if product and product['product_url'] not in seen_urls:
                    seen_urls.add(product['product_url'])
                    products.append(product)
                    new_on_page += 1

            if new_on_page == 0:
                cat_stale += 1
                if cat_stale >= 2:
                    break
            else:
                cat_stale = 0

            page += 1

        if ci % 20 == 0:
            print(f"    [{len(products)} products so far]", flush=True)

    return products


if __name__ == "__main__":
    run_scraper("博亚达", scrape)
