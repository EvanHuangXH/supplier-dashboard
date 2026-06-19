"""Fix SDS categories by clicking shipping tabs via Playwright (sdspod platform)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 6
BASE_URL = 'https://www.sdsdiy.com'

client = get_client()
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
with_cat = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).not_.is_('category','null').execute()
print(f'SDS: {with_cat.count}/{total.count} categorized', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

print('Loading...', flush=True)
try: page.goto(f'{BASE_URL}/portal/search', wait_until='networkidle', timeout=60000)
except: pass
time.sleep(4)

# Get shipping tabs
tabs = page.query_selector_all('.tab__style-3Wf6jT')
tab_names = [t.inner_text().strip() for t in tabs if t.inner_text().strip()]
print(f'Tabs: {tab_names}', flush=True)

fixed = 0
for tab_name in tab_names:
    # Click tab
    for t in page.query_selector_all('.tab__style-3Wf6jT'):
        if t.inner_text().strip() == tab_name:
            t.click(); time.sleep(3); break

    # Paginate through products under this tab
    pn = 1
    while pn <= 80:
        time.sleep(1.5)
        cards = page.query_selector_all('.newProductItem__style-WjoDb6')
        if not cards: break

        tab_fixed = 0
        for card in cards:
            try:
                name_el = card.query_selector('[class*=name]')
                if not name_el: continue
                name = name_el.inner_text().strip()
                if not name: continue
                client.table('products').update({'category': tab_name})\
                    .eq('supplier_id', SUPPLIER_ID).eq('name', name).execute()
                tab_fixed += 1
            except: pass

        if tab_fixed > 0: fixed += tab_fixed

        # Next page
        clicked = False
        for s in ['.ant-pagination-next:not(.ant-pagination-disabled)',
                   'li[title="Next Page"]:not(.ant-pagination-disabled)']:
            try:
                btn = page.query_selector(s)
                if btn: btn.click(); pn += 1; clicked = True; break
            except: pass
        if not clicked: break

    print(f'  {tab_name}: updated, total fixed={fixed}', flush=True)

with_cat2 = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).not_.is_('category','null').execute()
print(f'Done: {fixed} updated, now {with_cat2.count}/{total.count}', flush=True)
browser.close(); pw.stop()
