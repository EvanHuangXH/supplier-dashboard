"""Scraper for 博亚达 (xyldiy.com)."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_page, run_scraper


def scrape():
    """Scrape products from 博亚达."""
    products = []
    page = 1

    while True:
        url = f"http://www.xyldiy.com/product?page={page}"
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")

        # TODO: Update selectors after inspecting actual page structure
        cards = soup.select(".product-card")
        if not cards:
            break

        for card in cards:
            product = parse_product_card(card)
            if product:
                products.append(product)

        page += 1
        if page > 50:  # Safety limit
            break

    return products


def parse_product_card(card):
    """Parse a single product card. Update selectors per actual HTML."""
    # Placeholder — replace with actual selectors after site inspection
    name_el = card.select_one(".product-name") or card.select_one("h3") or card.select_one("a")
    price_el = card.select_one(".price") or card.select_one(".product-price")
    link_el = card.select_one("a") if card.name != "a" else card
    img_el = card.select_one("img")

    if not name_el or not link_el:
        return None

    name = name_el.get_text(strip=True)
    href = link_el.get("href", "")
    product_url = href if href.startswith("http") else f"http://www.xyldiy.com{href}"

    # Price parsing
    price = None
    price_unit = None
    if price_el:
        price_text = price_el.get_text(strip=True)
        import re
        price_match = re.search(r'[\d.]+', price_text)
        if price_match:
            price = float(price_match.group())

    return {
        "name": name,
        "description": None,
        "price": price,
        "price_unit": price_unit,
        "currency": "CNY",
        "delivery_days": None,
        "listed_at": None,
        "is_hot": False,
        "category": None,
        "material_tags": [],
        "image_url": img_el.get("src") if img_el else None,
        "product_url": product_url,
        "raw": {"supplier": "博亚达"},
    }


if __name__ == "__main__":
    run_scraper("博亚达", scrape)
