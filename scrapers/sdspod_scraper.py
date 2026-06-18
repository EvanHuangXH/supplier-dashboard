"""Sdspod scraper — single browser session, click-through pagination.
Handles both 海天城 and 艺之冠 (same platform).
"""
import sys, os, re, time
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from common import get_supplier_id, insert_product, log_scrape

SUPPLIER_NAME = None
BASE_URL = None


def scrape_all():
    supplier_id = get_supplier_id(SUPPLIER_NAME)
    all_products = []
    seen_names = set()

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=[
        '--no-sandbox','--disable-setuid-sandbox',
        '--disable-dev-shm-usage','--disable-gpu',
    ])
    page = browser.new_page(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36',
        viewport={'width': 1280, 'height': 900},
        locale='zh-CN'
    )

    def block(r):
        if r.request.resource_type in {'image','font','media'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    # Load initial page
    url = f"{BASE_URL}/portal/search"
    print(f"Loading {url}...")
    try:
        page.goto(url, wait_until='networkidle', timeout=60000)
    except:
        print("  networkidle timed out, continuing...")
    time.sleep(2)

    # Collect all warehouse names from sidebar
    warehouses = ['__ALL__']  # Start with "全部"
    try:
        root_items = page.query_selector_all('[class*=rootItem]')
        for item in root_items:
            name = item.inner_text().strip()
            if name and name != '全部' and name not in warehouses:
                warehouses.append(name)
        print(f"Found {len(warehouses)-1} warehouse filters")
    except:
        print("WARNING: Could not read warehouse menu")

    # Scrape each warehouse view
    for wh_idx, warehouse in enumerate(warehouses):
        print(f"\n--- [{wh_idx+1}/{len(warehouses)}] {warehouse} ---")

        # Click warehouse filter (skip for __ALL__)
        if warehouse != '__ALL__':
            try:
                clicked = False
                for item in page.query_selector_all('[class*=rootItem]'):
                    if item.inner_text().strip() == warehouse:
                        item.click()
                        time.sleep(3)
                        clicked = True
                        break
                if not clicked:
                    print("  Could not find/click warehouse, skipping")
                    continue
            except Exception as e:
                print(f"  Click error: {e}")
                continue

        # Paginate through this warehouse view
        page_num = 1
        stale_pages = 0

        while True:
            time.sleep(1.5)
            try:
                html = page.content()
            except:
                print("  Browser connection lost, skipping rest")
                break

            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('.productItem__style-JSa88h')

            if not cards:
                print(f"  No cards on page {page_num}")
                break

            new_on_page = 0
            for card in cards:
                product = _parse_card(card, category=warehouse if warehouse != '__ALL__' else None)
                if product and product['name'] not in seen_names:
                    seen_names.add(product['name'])
                    all_products.append(product)
                    new_on_page += 1

            print(f"  Page {page_num}: {new_on_page} new, {len(cards)} cards")

            if new_on_page == 0:
                stale_pages += 1
                if stale_pages >= 3:
                    print(f"  3 stale pages, moving to next warehouse")
                    break
            else:
                stale_pages = 0

            # Insert batch to DB periodically (every 2 pages)
            if len(all_products) % 40 == 0 and len(all_products) > 0:
                batch_new = 0
                recent = all_products[-40:]
                for p in recent:
                    if insert_product(supplier_id, p):
                        batch_new += 1
                print(f"  [DB] batch insert: {batch_new} new")

            # Click next page button
            clicked = False
            for sel in [
                '.ant-pagination-next:not(.ant-pagination-disabled)',
                'li[title="Next Page"]:not(.ant-pagination-disabled)',
                '.ant-pagination-item-active + li:not(.ant-pagination-disabled)',
            ]:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        page_num += 1
                        clicked = True
                        break
                except:
                    pass

            if not clicked:
                print(f"  No next-page button, done with this warehouse")
                break

            # Safety
            if page_num > 30:
                print(f"  30-page limit reached")
                break

    # Final DB insert for remaining
    print(f"\nTotal scraped: {len(all_products)} unique products")
    new_count = 0
    for p in all_products:
        if insert_product(supplier_id, p):
            new_count += 1
    log_scrape(supplier_id, len(all_products), new_count, 'success')
    print(f"Done: {len(all_products)} found, {new_count} new total")

    browser.close()
    pw.stop()


def _parse_card(card, category=None):
    name_el = card.select_one('.name__style-LDYYfw')
    if not name_el:
        return None
    name = name_el.get_text(strip=True)

    price = None
    price_el = card.select_one('.price__style-27FPVf')
    if price_el:
        nums = re.findall(r'[\d.]+', price_el.get_text(strip=True))
        if nums:
            try: price = float(nums[0])
            except: pass

    image_url = None
    img_div = card.select_one('.image__style-1BxEmp')
    if img_div:
        style = img_div.get('style', '')
        match = re.search(r'url\("([^"]+)"\)', style)
        if match:
            image_url = match.group(1)

    is_hot = False
    for tag in card.select('.tag__style-XyzH0Y'):
        if 'hot' in tag.get_text(strip=True).lower() or '热' in tag.get_text(strip=True):
            is_hot = True

    info_items = card.select('.infoItem__style-nHxDau')
    material_tags = []
    delivery_days = None
    desc_parts = []

    for item in info_items:
        text = item.get_text(strip=True)
        desc_parts.append(text)
        if '材质' in text:
            mat_text = text.split('：',1)[-1].strip() if '：' in text else text.split(':',1)[-1].strip() if ':' in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、\s]+', mat_text) if m.strip()]
        if '发货' in text or '时效' in text:
            nums = re.findall(r'(\d+)', text)
            if nums: delivery_days = int(nums[0])

    description = '; '.join(desc_parts) if desc_parts else None
    product_url = f"{BASE_URL}/portal/search#product={quote(name, safe='')}"

    return {
        'name': name, 'description': description, 'price': price,
        'price_unit': None, 'currency': 'CNY', 'delivery_days': delivery_days,
        'listed_at': None, 'is_hot': is_hot, 'category': category,
        'material_tags': material_tags, 'image_url': image_url,
        'product_url': product_url,
        'raw': {'supplier': SUPPLIER_NAME},
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python sdspod_scraper.py <supplier_name> <base_url>")
        sys.exit(1)
    SUPPLIER_NAME = sys.argv[1]
    BASE_URL = sys.argv[2]
    scrape_all()
