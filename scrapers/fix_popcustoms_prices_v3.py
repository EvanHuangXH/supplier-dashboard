"""Fix Popcustoms prices — networkidle wait + [class*=price] extraction."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 9
BASE_URL = 'https://www.popcustoms.cn'
client = get_client()

products = client.table('products').select('id,product_url').eq('supplier_id', SUPPLIER_ID).is_('price','null').execute()
print(f'Need prices: {len(products.data)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

fixed = 0
for i, p in enumerate(products.data):
    url = p['product_url'] or f'{BASE_URL}/products/{p["id"]}'
    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
        time.sleep(2)
    except:
        continue

    # Get first price from [class*=price]
    price_els = page.query_selector_all('[class*=price]')
    best_price = None
    for el in price_els:
        text = el.inner_text().strip()
        nums = re.findall(r'(\d+\.?\d{0,2})', text)
        if nums:
            prices = [float(n) for n in nums if 1 < float(n) < 10000]
            if prices:
                best_price = min(prices)  # lowest tier price
                break

    if best_price:
        client.table('products').update({'price': best_price}).eq('id', p['id']).execute()
        fixed += 1

    if (i + 1) % 50 == 0:
        remain = len(products.data) - i - 1
        print(f'  {i+1}/{len(products.data)}: {fixed} fixed, {remain} remain', flush=True)

print(f'\nDone: {fixed} prices updated', flush=True)

# Check final
total = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).execute()
with_price = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).not_.is_('price','null').execute()
print(f'Popcustoms: {with_price.count}/{total.count} have prices', flush=True)

browser.close(); pw.stop()
