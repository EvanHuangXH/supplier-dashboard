"""Fix SDS URLs — position-based matching across all shipping tabs."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 6
BASE_URL = 'https://www.sdsdiy.com'

client = get_client()
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
with_d = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%/detail/%').execute()
print(f'SDS before: {with_d.count}/{total.count}', flush=True)

prods = client.table('products').select('id,name').eq('supplier_id',SUPPLIER_ID).limit(5000).execute()
name_to_id = {}
for p in prods.data:
    name_to_id[p['name']] = p['id']
print(f'DB names: {len(name_to_id)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
page.route('**/*', lambda r: r.abort() if r.request.resource_type in {'font','media','image'} else r.continue_())

try: page.goto(f'{BASE_URL}/portal/search', wait_until='networkidle', timeout=60000)
except: pass
time.sleep(3)

tabs = page.query_selector_all('.tab__style-3Wf6jT')
tab_names = [t.inner_text().strip() for t in tabs if t.inner_text().strip()]
if not tab_names: tab_names = ['__DEFAULT__']
print(f'Tabs: {tab_names}', flush=True)

fixed = 0
for tab_name in tab_names:
    if tab_name != '__DEFAULT__':
        for t in page.query_selector_all('.tab__style-3Wf6jT'):
            if t.inner_text().strip() == tab_name:
                t.click(); time.sleep(3); break
        print(f'[{tab_name}]', flush=True)

    pn = 1
    stale = 0
    while pn <= 80:
        time.sleep(1)
        cards = page.query_selector_all('.newProductItem__style-WjoDb6')
        if not cards: break
        card_names = []
        for c in cards:
            try:
                n = c.query_selector('[class*=name]')
                card_names.append(n.inner_text().strip() if n else '')
            except:
                card_names.append('')

        api_items = page.evaluate(f'''async () => {{
            const r = await fetch('https://mapi.sdspod.com/products/page?size=20&page={pn}',
                {{headers:{{Origin:'{BASE_URL}'}}}});
            const j = await r.json();
            return j.items || [];
        }}''')
        if not api_items:
            stale += 1
            if stale >= 2: pn += 1; continue
            else: break

        pf = 0
        for i, item in enumerate(api_items):
            if i >= len(card_names): break
            cn = card_names[i]
            if not cn or cn not in name_to_id: continue
            pid = item.get('id')
            if not pid: continue
            try:
                client.table('products').update({'product_url': f'{BASE_URL}/portal/detail/{pid}'})\
                    .eq('id', name_to_id[cn]).execute()
                pf += 1; fixed += 1
                del name_to_id[cn]
            except: pass

        print(f'  P{pn}: {pf} fixed, {len(name_to_id)} remain', flush=True)
        if not name_to_id: break
        if pf == 0: stale += 1
        else: stale = 0
        if stale >= 3: break

        clicked = False
        for s in ['.ant-pagination-next:not(.ant-pagination-disabled)',
                   'li[title="Next Page"]:not(.ant-pagination-disabled)']:
            try:
                b = page.query_selector(s)
                if b: b.click(); pn += 1; clicked = True; time.sleep(1.5); break
            except: pass
        if not clicked: break

    print(f'  Tab done, {len(name_to_id)} remain', flush=True)

with_d2 = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%/detail/%').execute()
print(f'SDS after: {with_d2.count}/{total.count}', flush=True)
browser.close(); pw.stop()
