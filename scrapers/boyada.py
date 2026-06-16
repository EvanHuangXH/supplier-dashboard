"""Scraper for 博亚达 (diybyd.com)."""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_html, run_scraper

BASE_URL = "https://www.diybyd.com"


def scrape():
    """Scrape all products from 博亚达 product listing."""
    products = []
    page = 1

    while True:
        url = f"{BASE_URL}/custom?page={page}"
        print(f"  Fetching page {page}...")
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".card-product")

        if not cards:
            print(f"  No products found on page {page}, stopping.")
            break

        for card in cards:
            product = parse_product_card(card)
            if product:
                products.append(product)

        page += 1
        if page > 200:  # Safety limit
            break

    return products


def parse_product_card(card):
    """Parse a single .card-product element."""
    import re

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

    # Hot badge
    is_hot = False
    hot_badge = card.select_one(".badge.badge-warning")
    if hot_badge and "hot" in hot_badge.get_text(strip=True).lower():
        is_hot = True

    # New badge
    is_new = False
    new_badge = card.select_one(".badge.badge-success")
    if new_badge and "new" in new_badge.get_text(strip=True).lower():
        is_new = True

    # Product details from .small paragraphs
    small_ps = card.select(".card-body p.small")
    material_tags = []
    delivery_days = None
    description_parts = []

    for p in small_ps:
        text = p.get_text(strip=True)
        description_parts.append(text)

        # Extract material: "材质: 木质+棉绳"
        if "材质" in text:
            mat_text = text.split(":", 1)[-1].strip() if ":" in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、]', mat_text) if m.strip()]

        # Extract production time: "生产时间: 2-3 天"
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
        "category": None,
        "material_tags": material_tags,
        "image_url": image_url,
        "product_url": product_url,
        "raw": {"supplier": "博亚达", "is_new": is_new},
    }


if __name__ == "__main__":
    run_scraper("博亚达", scrape)
