"""Scraper for 蔚来视野 (wlsypod.com)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_page, run_scraper


def scrape():
    products = []
    page = 1
    while True:
        url = f"https://www.wlsypod.com/product?page={page}"
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".product-card")
        if not cards:
            break
        for card in cards:
            product = parse_product_card(card)
            if product:
                products.append(product)
        page += 1
        if page > 50:
            break
    return products


def parse_product_card(card):
    name_el = card.select_one(".product-name") or card.select_one("h3") or card.select_one("a")
    price_el = card.select_one(".price") or card.select_one(".product-price")
    link_el = card.select_one("a") if card.name != "a" else card
    img_el = card.select_one("img")

    if not name_el or not link_el:
        return None

    name = name_el.get_text(strip=True)
    href = link_el.get("href", "")
    product_url = href if href.startswith("http") else f"https://www.wlsypod.com{href}"

    price = None
    if price_el:
        import re
        price_text = price_el.get_text(strip=True)
        match = re.search(r'[\d.]+', price_text)
        if match:
            price = float(match.group())

    return {
        "name": name,
        "description": None,
        "price": price,
        "price_unit": None,
        "currency": "CNY",
        "delivery_days": None,
        "listed_at": None,
        "is_hot": False,
        "category": None,
        "material_tags": [],
        "image_url": img_el.get("src") if img_el else None,
        "product_url": product_url,
        "raw": {"supplier": "蔚来视野"},
    }


if __name__ == "__main__":
    run_scraper("蔚来视野", scrape)
