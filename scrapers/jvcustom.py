"""Scraper for JVCustom (jvcustom.com) — 8ding platform with Playwright."""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from common import get_supplier_id, insert_product, log_scrape, get_client

BASE_URL = "https://www.jvcustom.com"
SUPPLIER_ID = 7


def scrape():
    client = get_client()
    all_products = []
    seen_urls = set()

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

    def block(r):
        if r.request.resource_type in {'font', 'media'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    # Get categories from filter dropdown
    print('Loading page...', flush=True)
    try: page.goto(f'{BASE_URL}/custom', wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(3)

    # Extract categories from filter panel
    cat_elements = page.query_selector_all('[class*=categ] a, [class*=categ] button, #category_filter option, .filter-item')
    categories = []
    for el in cat_elements:
        try:
            text = el.inner_text().strip()
            if text and len(text) < 50 and '全部' not in text:
                categories.append(text)
        except: pass
    # Also try clicking the filter to get options
    if not categories:
        cat_els = page.query_selector_all('#category_filter option, select[name*=categ] option, .dropdown-menu a')
        for el in cat_els:
            try:
                val = el.get_attribute('value') or ''
                text = el.inner_text().strip()
                if text and val and '全部' not in text:
                    categories.append(text)
            except: pass
    print(f'Categories: {len(categories)}', flush=True)

    # Scrape all pages (no category filter = all products)
    pn = 1
    stale = 0
    while pn <= 50:
        url = f'{BASE_URL}/custom/productItem?page={pn}' if pn > 1 else f'{BASE_URL}/custom'
        try: page.goto(url, wait_until='networkidle', timeout=30000)
        except: break
        time.sleep(2)

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('.card-product') or soup.select('.card')
        if not cards:
            stale += 1
            if stale >= 2: break
            pn += 1
            continue

        new_p = 0
        for card in cards:
            product = parse_card(card)
            if product and product['product_url'] not in seen_urls:
                seen_urls.add(product['product_url'])
                all_products.append(product)
                new_p += 1
                # Batch insert every 30
                if len(all_products) % 30 == 0:
                    insert_product(SUPPLIER_ID, product)

        print(f'  P{pn}: {new_p}N/{len(cards)}C | total={len(all_products)}', flush=True)

        if new_p == 0:
            stale += 1
            if stale >= 3: break
        else:
            stale = 0

        pn += 1

    # Final insert
    nc = 0
    for p in all_products:
        if insert_product(SUPPLIER_ID, p): nc += 1
    log_scrape(SUPPLIER_ID, len(all_products), nc, 'success')
    print(f'Done: {len(all_products)} found, {nc} new', flush=True)
    browser.close(); pw.stop()


def parse_card(card):
    name_link = card.select_one('h3.card-title a') or card.select_one('.card-body h3 a') or card.select_one('a[href*="/"]')
    if not name_link:
        return None
    name = name_link.get_text(strip=True)
    href = name_link.get('href', '')
    product_url = href if href.startswith('http') else f'{BASE_URL}{href}'

    price = None
    money_el = card.select_one('.money')
    if money_el:
        try: price = float(money_el.get('data-money', ''))
        except: pass

    image_url = None
    img_el = card.select_one('img.lazy') or card.select_one('.card-image img')
    if img_el:
        image_url = img_el.get('data-original') or img_el.get('src')

    material_tags = []
    delivery_days = None
    for p in card.select('p.small, .card-body p.small'):
        text = p.get_text(strip=True)
        if '材质' in text:
            mt = text.split(':',1)[-1].strip() if ':' in text else text
            material_tags = [m.strip() for m in re.split(r'[+,,，、]', mt) if m.strip()]
        if '时间' in text:
            nums = re.findall(r'(\d+)', text)
            if nums: delivery_days = int(nums[0])

    return {
        'name': name, 'description': None, 'price': price,
        'price_unit': None, 'currency': 'CNY', 'delivery_days': delivery_days,
        'listed_at': None, 'is_hot': bool(card.select_one('.badge-warning')),
        'category': None, 'material_tags': material_tags,
        'image_url': image_url, 'product_url': product_url,
        'raw': {'supplier': 'JVCustom'},
    }


if __name__ == '__main__':
    scrape()
