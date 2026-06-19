"""Fix categories for ALL 8ding platform suppliers via Playwright sidebar clicking."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SITES = [
    ('博亚达', 'https://www.diybyd.com', 1),
    ('蔚来视野', 'https://www.wlsypod.com', 4),
    ('八点多', 'https://www.8ding.com', 10),
    ('方圆定制', 'https://www.fypod.com', 12),
]

client = get_client()

for supplier_name, base_url, sid in SITES:
    # Check how many need categories
    total = client.table('products').select('id',count='exact').eq('supplier_id',sid).execute()
    with_cat = client.table('products').select('id',count='exact').eq('supplier_id',sid).not_.is_('category','null').execute()
    need = total.count - with_cat.count
    if need == 0:
        print(f'{supplier_name}: all done! ({with_cat.count}/{total.count})')
        continue
    print(f'{supplier_name}: {need} need category ({with_cat.count}/{total.count})', flush=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    def block(r):
        if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    try: page.goto(f'{base_url}/custom', wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(3)

    # Get category links from sidebar
    cat_links = page.query_selector_all('.my-product-category a')
    categories = []
    for link in cat_links:
        try:
            text = link.inner_text().strip()
            if text and len(text) < 60 and '全部' not in text:
                categories.append(text)
        except: pass
    categories = list(dict.fromkeys(categories))
    print(f'  Categories: {len(categories)}', flush=True)

    fixed = 0
    for ci, cat_name in enumerate(categories):
        # Click category
        clicked = False
        for link in page.query_selector_all('.my-product-category a'):
            try:
                if link.inner_text().strip() == cat_name:
                    link.click()
                    time.sleep(2)
                    clicked = True
                    break
            except: pass
        if not clicked: continue

        # Get products on current page
        cards = page.query_selector_all('.card-product')
        cat_fixed = 0
        for card in cards:
            try:
                name_el = card.query_selector('.card-body h3 a') or card.query_selector('h3 a')
                if not name_el: continue
                name = name_el.inner_text().strip()
                if not name: continue
                client.table('products').update({'category': cat_name})\
                    .eq('supplier_id', sid).eq('name', name).execute()
                cat_fixed += 1
            except: pass

        if cat_fixed > 0:
            fixed += cat_fixed
        if ci % 20 == 0:
            print(f'  [{ci+1}/{len(categories)}] {cat_name}: {cat_fixed} updated', flush=True)

    with_cat2 = client.table('products').select('id',count='exact').eq('supplier_id',sid).not_.is_('category','null').execute()
    print(f'  Done: {fixed} updated, now {with_cat2.count}/{total.count}', flush=True)
    browser.close()
    pw.stop()

print('\nAll 8ding sites processed!')
