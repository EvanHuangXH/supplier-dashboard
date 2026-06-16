"""Scraper for 海天城 (htccustom.com) — sdspod platform."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from bs4 import BeautifulSoup
from common import fetch_html, run_scraper

BASE_URL = "http://www.htccustom.com"


def scrape():
    products = []
    page = 1
    while True:
        url = f"{BASE_URL}/portal/search?page={page}"
        print(f"  Fetching page {page}...")
        html = fetch_html(url, wait_for="networkidle")
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".productItem__style-JSa88h")
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
    # Name
    name_el = card.select_one(".name__style-LDYYfw")
    if not name_el:
        return None
    name = name_el.get_text(strip=True)

    # Price
    price = None
    price_el = card.select_one(".price__style-27FPVf")
    if price_el:
        nums = re.findall(r'[\d.]+', price_el.get_text(strip=True))
        if nums:
            price = float(nums[0])

    # Image from background-image style
    image_url = None
    img_div = card.select_one(".image__style-1BxEmp")
    if img_div:
        style = img_div.get("style", "")
        match = re.search(r'url\("([^"]+)"\)', style)
        if match:
            image_url = match.group(1)

    # Tags: new, hot
    is_hot = False
    tags = card.select(".tag__style-XyzH0Y")
    for tag in tags:
        text = tag.get_text(strip=True)
        if "hot" in text.lower() or "热" in text:
            is_hot = True

    # Hover detail items
    info_items = card.select(".infoItem__style-nHxDau")
    material_tags = []
    delivery_days = None
    desc_parts = []

    for item in info_items:
        text = item.get_text(strip=True)
        desc_parts.append(text)

        if "材质" in text:
            mat_text = text.split("：", 1)[-1].strip() if "：" in text else text.split(":", 1)[-1].strip() if ":" in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、\s]+', mat_text) if m.strip()]

        if "发货" in text or "时效" in text:
            nums = re.findall(r'(\d+)', text)
            if nums:
                delivery_days = int(nums[0])

    # Use search page as product URL (no individual product pages)
    product_url = f"{BASE_URL}/portal/search"

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
        "raw": {"supplier": "海天城"},
    }


if __name__ == "__main__":
    run_scraper("海天城", scrape)
