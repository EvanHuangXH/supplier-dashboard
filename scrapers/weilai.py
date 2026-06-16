"""Scraper for 蔚来视野 (wlsypod.com) — same platform as 博亚达 (8ding)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_html, run_scraper

BASE_URL = "https://www.wlsypod.com"


def scrape():
    products = []
    page = 1
    while True:
        url = f"{BASE_URL}/custom?page={page}"
        print(f"  Fetching page {page}...")
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".card-product")
        if not cards:
            break
        for card in cards:
            product = parse_product_card(card)
            if product:
                products.append(product)
        page += 1
        if page > 200:
            break
    return products


def parse_product_card(card):
    name_link = card.select_one(".card-body h3 a")
    if not name_link:
        return None

    name = name_link.get_text(strip=True)
    href = name_link.get("href", "")
    product_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    # Price from data-money
    price = None
    money_el = card.select_one(".money")
    if money_el:
        try:
            price = float(money_el.get("data-money", ""))
        except (ValueError, TypeError):
            pass

    # Image from data-original (lazy loaded)
    image_url = None
    img_el = card.select_one(".card-image img")
    if img_el:
        image_url = img_el.get("data-original") or img_el.get("src")

    # Hot badge
    hot_badge = card.select_one(".badge.badge-warning")
    is_hot = bool(hot_badge and "hot" in hot_badge.get_text(strip=True).lower())

    # Badges
    new_badge = card.select_one(".badge.badge-success") or card.select_one(".badge.bg-white.border-success")

    # Product details
    small_ps = card.select(".card-body p.small")
    material_tags = []
    delivery_days = None
    desc_parts = []

    for p in small_ps:
        text = p.get_text(strip=True)
        desc_parts.append(text)
        if "材质" in text:
            mat_text = text.split(":", 1)[-1].strip() if ":" in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、]', mat_text) if m.strip()]
        if "生产时间" in text or "时间" in text:
            nums = re.findall(r'(\d+)', text)
            if nums:
                delivery_days = int(nums[0])

    return {
        "name": name,
        "description": "; ".join(desc_parts) if desc_parts else None,
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
        "raw": {"supplier": "蔚来视野"},
    }


if __name__ == "__main__":
    run_scraper("蔚来视野", scrape)
