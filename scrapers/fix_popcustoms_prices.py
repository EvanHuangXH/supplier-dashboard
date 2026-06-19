"""Fix Popcustoms prices by scraping product detail pages."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 9
BASE_URL = 'https://www.popcustoms.cn'

client = get_client()
products = client.table('products').select('id,product_url').eq('supplier_id', SUPPLIER_ID).is_('price', 'null').limit(5000).execute()
print(f'Products without price: {len(products.data)}', flush=True)

if not products.data:
    print('All have prices!')
    exit()

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

def block(r):
    if r.request.resource_type in {'font', 'media'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

fixed = 0
for i, p in enumerate(products.data):
    pid = p['id']
    url = p['product_url'] or f'{BASE_URL}/products/{pid}'

    for retry in range(2):
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(4)  # Wait for Vue to render
        except:
            continue

        # Extract price from first price element
        price_els = page.query_selector_all('[class*=price]')
        if price_els: break
        time.sleep(3)  # Extra wait if no price elements

    # Also try getting price from page HTML if no elements found
    if not price_els:
        html = page.content()
        # Find price in the format: any XX.XX number that looks like a price
        all_prices = re.findall(r'(\d+\.\d{2})', html)
        if all_prices:
            prices_float = [float(p) for p in all_prices if 1 < float(p) < 1000]
            if prices_float:
                best_price = min(prices_float)
                client.table('products').update({'price': best_price}).eq('id', pid).execute()
                fixed += 1
        continue

    for el in price_els:
        text = el.inner_text().strip()
        nums = re.findall(r'\d+\.\d{2}', text)
        if len(nums) >= 2:
            # nums[0] = inquiry price (bulk), nums[1] = 100+ tier price
            # Use the second price as the base price
            best_price = float(nums[1]) if len(nums) > 1 else float(nums[0])
            client.table('products').update({'price': best_price}).eq('id', pid).execute()
            fixed += 1
            break

    if (i + 1) % 50 == 0:
        print(f'  {i+1}/{len(products.data)}: {fixed} fixed', flush=True)

print(f'\nDone: {fixed} prices updated', flush=True)
browser.close(); pw.stop()
