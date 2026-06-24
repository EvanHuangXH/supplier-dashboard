"""Fix SDS URLs — keyword search via URL + position-match with API."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 6
BASE_URL = 'https://www.sdsdiy.com'
client = get_client()

prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
print(f'Fake URLs: {len(prods.data)}', flush=True)

# Build name→id, using short key for matching
name_to_id = {}
for p in prods.data:
    name_to_id[p['name']] = p['id']

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width':1920,'height':1080}, locale='zh-CN')
page.route('**/*', lambda r: r.abort() if r.request.resource_type in {'font','media','image'} else r.continue_())

# Load page for auth
try: page.goto(f'{BASE_URL}/portal/search', wait_until='networkidle', timeout=60000)
except: pass
time.sleep(3)

fixed = 0
names = list(name_to_id.keys())

for i, name in enumerate(names):
    # Search by keyword (use first word or short phrase)
    keyword = name[:20]  # First 20 chars as search
    try:
        page.goto(f'{BASE_URL}/portal/search?keyword={keyword}', wait_until='networkidle', timeout=30000)
        time.sleep(2)

        cards = page.query_selector_all('.newProductItem__style-WjoDb6')
        if not cards:
            continue

        # Get card names and API data by position
        card_names = []
        for c in cards:
            try:
                n = c.query_selector('[class*=name]')
                card_names.append(n.inner_text().strip() if n else '')
            except:
                card_names.append('')

        # Get API data for same page
        api_items = page.evaluate('''async () => {
            const r = await fetch('https://mapi.sdspod.com/products/page?size=20&page=1',
                {headers:{Origin:'https://www.sdsdiy.com'}});
            const j = await r.json();
            return j.items || [];
        }''')

        # Match: exact name match in cards
        for ci, cn in enumerate(card_names):
            if cn == name and ci < len(api_items):
                pid = api_items[ci].get('id')
                if pid:
                    try:
                        client.table('products').update({'product_url': f'{BASE_URL}/portal/detail/{pid}'})\
                            .eq('id', name_to_id[name]).execute()
                        del name_to_id[name]
                        fixed += 1
                    except: pass
                    break
    except:
        continue

    if (i + 1) % 50 == 0:
        print(f'  {i+1}/{len(names)}: {fixed} fixed, {len(name_to_id)} remain', flush=True)

print(f'\nDone: {fixed} URLs', flush=True)

total = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').execute()
print(f'SDS: {total.count-fake.count}/{total.count} real', flush=True)
browser.close(); pw.stop()
