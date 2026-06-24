"""Fix Popcustoms prices — scrape correct prices from product pages."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 9
client = get_client()

prods = client.table('products').select('id,product_url').eq('supplier_id', SUPPLIER_ID).limit(5000).execute()
print(f'Total: {len(prods.data)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width':1920,'height':1080}, locale='zh-CN')
page.route('**/*', lambda r: r.abort() if r.request.resource_type in {'font','media'} else r.continue_())

fixed = 0
for i, p in enumerate(prods.data):
    url = p['product_url']
    if not url or 'popcustoms.cn' not in url:
        url = f'https://www.popcustoms.cn/products/{p["id"]}'

    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
        time.sleep(3)
    except:
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            time.sleep(5)
        except: continue

    # Get ALL text in price elements
    price_text = ''
    for el in page.query_selector_all('[class*=price]'):
        price_text += el.inner_text().strip() + '\n'

    if not price_text:
        continue

    # Find all XX.XX numbers
    all_nums = re.findall(r'(\d+\.\d{2})', price_text)
    if not all_nums:
        continue

    # Filter: keep only reasonable prices (1-5000 range, skip quantities like 100.00)
    candidates = []
    for n in all_nums:
        v = float(n)
        if 1 < v < 5000 and v != 100.00 and v != 50.00:
            candidates.append(v)

    if candidates:
        # Use the FIRST price found (usually the unit/display price)
        correct_price = candidates[0]
        client.table('products').update({'price': correct_price}).eq('id', p['id']).execute()
        fixed += 1

    if (i+1) % 100 == 0:
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed', flush=True)

print(f'\nDone: {fixed} prices updated', flush=True)

# Verify
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
wp = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).not_.is_('price','null').execute()
print(f'Popcustoms: {wp.count}/{total.count} have prices', flush=True)

# Show samples
r = client.table('products').select('name,price').eq('supplier_id',SUPPLIER_ID).not_.is_('price','null').limit(10).execute()
print('Sample prices:')
for p in r.data:
    print(f'  {p["name"][:40]}... {p["price"]}', flush=True)

browser.close(); pw.stop()
