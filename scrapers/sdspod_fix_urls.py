"""Fix sdspod product URLs: batch click all cards, collect detail page URLs."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

client = get_client()

for supplier_name, base_url, sid in [
    ('海天城', 'http://www.htccustom.com', 2),
    ('艺之冠', 'http://ykartwood.com', 3),
]:
    prods = client.table('products').select('id,name').eq('supplier_id', sid)\
        .not_.like('product_url', '%/detail/%').order('id').limit(1000).execute()
    if not prods.data:
        print(f'{supplier_name}: all done!')
        continue

    # Build name→id lookup
    name_to_id = {p['name']: p['id'] for p in prods.data}
    print(f'{supplier_name}: {len(name_to_id)} to fix', flush=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    context = browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    page = context.new_page()

    # Track new pages
    detail_pages = []
    def on_page(p):
        detail_pages.append(p)
    context.on('page', on_page)

    # Paginate through all product pages
    page_num = 1
    fixed = 0

    while page_num <= 30:
        url = f'{base_url}/portal/search?page={page_num}' if page_num > 1 else f'{base_url}/portal/search'
        print(f'  Page {page_num}...', flush=True)

        if page_num == 1:
            try: page.goto(url, wait_until='networkidle', timeout=60000)
            except: pass
        else:
            # Click next page button
            clicked = False
            for sel in ['.ant-pagination-next:not(.ant-pagination-disabled)',
                         'li[title="Next Page"]:not(.ant-pagination-disabled)']:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        time.sleep(3)
                        clicked = True
                        break
                except: pass
            if not clicked:
                print('    no next page, done')
                break

        time.sleep(2)

        # Get all cards on this page
        cards = page.query_selector_all('.productItem__style-JSa88h')
        if not cards:
            # Check if page has different content
            try:
                html = page.content()
                cards_check = len(re.findall(r'productItem__style', html))
                if cards_check == 0:
                    print(f'    no cards, done')
                    break
            except: pass

        # Click each card's image
        for card in cards:
            name_el = card.query_selector('.name__style-LDYYfw')
            if not name_el: continue
            card_name = name_el.inner_text().strip()
            if card_name not in name_to_id: continue

            img_div = card.query_selector('.image__style-1BxEmp')
            if not img_div: continue

            try:
                img_div.click()
                time.sleep(0.8)  # Short wait between clicks
            except:
                pass

        # Process collected detail pages
        for dp in detail_pages:
            try:
                detail_url = dp.url
                if '/detail/' not in detail_url:
                    try: dp.close()
                    except: pass
                    continue

                # Get product name from detail page
                try:
                    dp.bring_to_front()
                    dp.wait_for_load_state('domcontentloaded', timeout=5000)
                    dp.wait_for_timeout(1000)
                    # Try common title selectors
                    for sel in ['h1', '.title', '[class*=title]', '[class*=name]', '.product-title']:
                        el = dp.query_selector(sel)
                        if el:
                            detail_name = el.inner_text().strip()
                            if detail_name and detail_name in name_to_id:
                                rec_id = name_to_id[detail_name]
                                client.table('products').update({'product_url': detail_url})\
                                    .eq('id', rec_id).execute()
                                del name_to_id[detail_name]
                                fixed += 1
                            break
                except:
                    pass
                try: dp.close()
                except: pass
            except:
                pass

        detail_pages.clear()
        print(f'    {fixed} fixed, {len(name_to_id)} remain', flush=True)

        if len(name_to_id) == 0:
            print(f'    All done!')
            break

        page_num += 1

    print(f'  Final: {fixed} URLs updated', flush=True)
    browser.close()
    pw.stop()

# Report
print()
for sid, name in [(2,'海天城'),(3,'艺之冠')]:
    total = client.table('products').select('id',count='exact').eq('supplier_id',sid).execute()
    with_d = client.table('products').select('id',count='exact').eq('supplier_id',sid)\
        .like('product_url','%/detail/%').execute()
    print(f'{name}: {with_d.count}/{total.count} detail URLs')
