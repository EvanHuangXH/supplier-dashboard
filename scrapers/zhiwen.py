"""Scraper for 指纹科技 (hicustom.com) — domestic + JIT products."""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_html, run_scraper


def scrape_tab(base_url, tab_label, max_pages=100):
    """Scrape one tab (domestic or JIT). Returns list of product dicts."""
    products = []
    page = 1
    stale_pages = 0
    seen_names = set()

    while True:
        url = f"{base_url}&page={page}" if "?" in base_url else f"{base_url}?page={page}"
        print(f"  [{tab_label}] Fetching page {page}...")
        html = fetch_html(url, wait_for="domcontentloaded")
        # Vue SPA needs time to render; page 1 is slower (initial JS bootstrap)
        wait = 10 if page == 1 else 6
        time.sleep(wait)

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".product-card")

        if not cards:
            # Page 1 might need a retry (cold load)
            if page == 1:
                print(f"  [{tab_label}] Page 1 empty, retrying after extra wait...")
                time.sleep(8)
                cards = soup.select(".product-card")
            if not cards:
                print(f"  [{tab_label}] No products on page {page}, stopping.")
                break

        new_on_page = 0
        for card in cards:
            product = parse_product_card(card, url, category=tab_label)
            if product:
                products.append(product)
                if product["name"] not in seen_names:
                    seen_names.add(product["name"])
                    new_on_page += 1

        print(f"  [{tab_label}] Page {page}: {new_on_page} new, {len(cards)} total")

        if new_on_page == 0:
            stale_pages += 1
            if stale_pages >= 3:
                print(f"  [{tab_label}] Stopping: 3 stale pages.")
                break
        else:
            stale_pages = 0

        page += 1
        if page > max_pages:
            break

    return products


def scrape():
    """Scrape both domestic and JIT tabs."""
    all_products = []

    # Tab 1: Domestic (国内发货) — 905 products
    print("\n  --- Domestic tab (国内) ---")
    domestic = scrape_tab(
        "https://www.hicustom.com/productType/allGoods?page=1",
        "国内"
    )
    all_products.extend(domestic)
    print(f"  Domestic total: {len(domestic)}")

    # Tab 2: JIT overseas (海外本土货盘) — 560 products
    print("\n  --- JIT tab (海外) ---")
    jit = scrape_tab(
        "https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1",
        "海外"
    )
    all_products.extend(jit)
    print(f"  JIT total: {len(jit)}")

    return all_products


def parse_product_card(card, page_url, category=None):
    # Name: .name-content > span.name
    name_el = card.select_one(".name")
    if not name_el:
        return None

    name = name_el.get_text(strip=True)

    # Price: .price .prod_price .price-num
    price = None
    price_num = card.select_one(".price-num")
    if price_num:
        try:
            price = float(price_num.get_text(strip=True))
        except (ValueError, TypeError):
            pass

    # Image: .product-img
    image_url = None
    img_el = card.select_one(".product-img")
    if img_el:
        image_url = img_el.get("src")
        if image_url and image_url.startswith("/"):
            image_url = f"https://www.hicustom.com{image_url}"

    # Hot tag
    is_hot = bool(card.select_one(".hot-tag"))

    # Delivery info from .send
    delivery_days = None
    send_el = card.select_one(".send")
    if send_el:
        send_text = send_el.get_text(strip=True)
        nums = re.findall(r'(\d+)', send_text)
        if nums:
            delivery_days = int(nums[0])

    # Generate unique product URL using name (Vue SPA has no individual product pages)
    from urllib.parse import quote
    product_url = f"https://www.hicustom.com/productType/allGoods#product={quote(name, safe='')}"

    return {
        "name": name,
        "description": None,
        "price": price,
        "price_unit": None,
        "currency": "CNY",
        "delivery_days": delivery_days,
        "listed_at": None,
        "is_hot": is_hot,
        "category": category,
        "material_tags": [],
        "image_url": image_url,
        "product_url": product_url,
        "raw": {"supplier": "指纹科技"},
    }


if __name__ == "__main__":
    run_scraper("指纹科技", scrape)
