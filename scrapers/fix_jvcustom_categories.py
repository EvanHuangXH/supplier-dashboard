"""Fix JVCustom categories — click through AJAX category filter and update DB."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

BASE_URL = 'https://www.jvcustom.com'
SUPPLIER_ID = 7

client = get_client()
pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

def block(r):
    if r.request.resource_type in {'font', 'media'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

print('Loading page...', flush=True)
try: page.goto(f'{BASE_URL}/custom', wait_until='networkidle', timeout=60000)
except: pass
time.sleep(3)

# Get category filter items
cat_els = page.query_selector_all('[class*=categ] a, [class*=categ] li, .filter-item, #category_filter option')
categories = []
for el in cat_els:
    try:
        text = el.inner_text().strip()
        if text and len(text) < 60 and '全部' not in text and 'NEW' not in text and 'SALE' not in text:
            categories.append(text)
    except: pass

# Dedup
categories = list(dict.fromkeys(categories))
print(f'Categories: {len(categories)}', flush=True)
for c in categories[:10]:
    print(f'  {c}')
if len(categories) > 10:
    print(f'  ... and {len(categories)-10} more')

# For each category, click it and update products on the visible page
fixed_total = 0
for ci, cat_name in enumerate(categories):
    print(f'[{ci+1}/{len(categories)}] {cat_name[:50]}', end=' ', flush=True)

    # Click the category
    clicked = False
    for el in page.query_selector_all('[class*=categ] a, [class*=categ] li, .filter-item'):
        try:
            if el.inner_text().strip() == cat_name:
                el.click()
                time.sleep(2)
                clicked = True
                break
        except: pass

    if not clicked:
        # Try clicking by text
        try:
            page.click(f'text={cat_name}', timeout=3000)
            time.sleep(2)
            clicked = True
        except: pass

    if not clicked:
        print('skip', flush=True)
        continue

    # Read product cards on current page
    cards = page.query_selector_all('.card-product')
    cat_fixed = 0
    for card in cards:
        try:
            name_el = card.query_selector('h3.card-title a') or card.query_selector('.card-body h3 a')
            if not name_el: continue
            name = name_el.inner_text().strip()
            # Update category
            client.table('products').update({'category': cat_name})\
                .eq('supplier_id', SUPPLIER_ID).eq('name', name).execute()
            cat_fixed += 1
        except: pass

    print(f'{cat_fixed} updated', flush=True)
    fixed_total += cat_fixed

print(f'\nTotal: {fixed_total} category updates', flush=True)
browser.close(); pw.stop()
