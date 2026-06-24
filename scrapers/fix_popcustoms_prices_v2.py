"""Fix Popcustoms prices from listing page (cards show prices)."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 9
BASE_URL = 'https://www.popcustoms.cn'

client = get_client()
total = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).execute()
with_price = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).not_.is_('price','null').execute()
need = total.count - with_price.count
print(f'Need prices: {need}/{total.count}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

# Load first page of listing
page.goto(f'{BASE_URL}/products?page=1&limit=48&is_ship_from_china=1',
          wait_until='networkidle', timeout=60000)
time.sleep(5)

# Get all products from DB for name lookup
db_prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID).is_('price','null').execute()
name_to_id = {}
for p in db_prods.data:
    name_to_id[p['name']] = p['id']
print(f'DB names to match: {len(name_to_id)}', flush=True)

# Also try API-based price extraction
# The shipping filter affects listings
fixed = 0
for ship_label, ship_val in [('国内发货', 1), ('海外发货', 0)]:
    for pn in range(1, 20):
        page.goto(f'{BASE_URL}/products?page={pn}&limit=48&is_ship_from_china={ship_val}',
                  wait_until='networkidle', timeout=60000)
        time.sleep(4)

    # Get all visible text
    body = page.evaluate('() => document.body.innerText')

    # Try name matching with and without shipping suffixes
    lines = body.split('\n')
    page_fixed = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        price_match = re.search(r'[¥￥]\s*(\d+\.?\d{0,2})', line)
        if price_match and i > 0:
            price = float(price_match.group(1))
            for j in range(i-1, max(i-5, -1), -1):
                raw_name = lines[j].strip()
                if raw_name and len(raw_name) > 3:
                    # Try exact match first, then strip suffixes
                    for try_name in [raw_name,
                                     re.sub(r'[-–]\s*(国内|海外|CN|US|EU).*$', '', raw_name).strip(),
                                     raw_name.split('-')[0].strip()]:
                        if try_name in name_to_id:
                            try:
                                client.table('products').update({'price': price})\
                                    .eq('id', name_to_id[try_name]).execute()
                                del name_to_id[try_name]
                                page_fixed += 1; fixed += 1
                            except: pass
                            break
                    break
        i += 1

    print(f'  P{pn}: {page_fixed} updated, {len(name_to_id)} remain', flush=True)
    if not name_to_id or page_fixed == 0:
        break

with_price2 = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).not_.is_('price','null').execute()
print(f'\nDone: {with_price2.count}/{total.count} have prices', flush=True)
browser.close(); pw.stop()
