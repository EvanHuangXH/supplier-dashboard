"""Fix 指纹科技 URLs — position-based matching from listing page."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
BASE_URL = 'https://www.hicustom.com'

client = get_client()
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
with_spu = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%/spu%').execute()
print(f'指纹科技: {with_spu.count}/{total.count} SPU URLs', flush=True)

prods = client.table('products').select('id,name').eq('supplier_id',SUPPLIER_ID).limit(5000).execute()
name_to_id = {}
for p in prods.data:
    if p['name'] not in name_to_id:
        name_to_id[p['name']] = p['id']
print(f'DB unique names: {len(name_to_id)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

# Load JIT listing
print('Loading JIT listing...', flush=True)
try: page.goto(f'{BASE_URL}/productType/allGoods?isSearch=1&tab=jit&page=1', wait_until='networkidle', timeout=60000)
except: pass
time.sleep(4)

fixed = 0
pn = 1
while pn <= 50 and name_to_id:
    time.sleep(1.5)
    cards = page.query_selector_all('.product-card')
    if not cards: break

    # Get card names
    card_names = []
    for card in cards:
        try:
            name_el = card.query_selector('.name')
            card_names.append(name_el.inner_text().strip() if name_el else '')
        except:
            card_names.append('')

    # Call SPU API
    api_result = page.evaluate(f'''async () => {{
        const resp = await fetch('https://apigw.hihumbird.com/spu-itg/uct/v1/spus/page', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                app_id: '2483999', delivery_period_filters: [], weight_filters: [],
                sort_center_app_country_codes: ['US','IT','ES','CA','MX','UK','AU','JP','BR','MY','DE','PH','PL','TH','ID'],
                is_filter_reference: 1, size: 100, current: {pn}
            }})
        }});
        return await resp.json();
    }}''')
    api_items = api_result.get('data', {}).get('list', [])
    if not api_items: break

    page_fixed = 0
    for i, item in enumerate(api_items):
        if i >= len(card_names): break
        card_name = card_names[i]
        if not card_name or card_name not in name_to_id:
            # Try normalized matching
            norm_card = re.sub(r'\s+', '', card_name)
            for db_name in list(name_to_id.keys()):
                if re.sub(r'\s+', '', db_name) == norm_card:
                    card_name = db_name
                    break
            else:
                continue

        spu_id = item.get('id', '')
        if not spu_id: continue
        product_url = f'https://jit.hicustom.com/spu?id={spu_id}'

        db_id = name_to_id[card_name]
        try:
            client.table('products').update({'product_url': product_url}).eq('id', db_id).execute()
            page_fixed += 1
            del name_to_id[card_name]
        except: pass

    fixed += page_fixed
    print(f'  P{pn}: {page_fixed} fixed, {len(name_to_id)} remain', flush=True)

    if not name_to_id: break
    if page_fixed == 0:
        stale = getattr(sys.modules[__name__], '_stale', 0) + 1
        setattr(sys.modules[__name__], '_stale', stale)
        if stale >= 5: break
    pn += 1

print(f'\nDone: {fixed} fixed', flush=True)
with_spu2 = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%/spu%').execute()
print(f'指纹科技: {with_spu2.count}/{total.count} SPU URLs', flush=True)
browser.close(); pw.stop()
