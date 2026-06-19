"""Fix sdspod categories via API — directly UPDATE existing products' category field."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

client = get_client()

SITES = [
    ('海天城', 'http://www.htccustom.com', 2, 'http://www.htccustom.com'),
    ('艺之冠', 'http://ykartwood.com', 3, 'http://ykartwood.com'),
    ('SDS', 'https://www.sdsdiy.com', 6, 'https://www.sdsdiy.com'),
]

for supplier_name, base_url, sid, api_origin in SITES:
    # Get products with NULL category
    prods = client.table('products').select('id,name').eq('supplier_id', sid)\
        .is_('category', 'null').limit(5000).execute()
    if not prods.data:
        print(f'{supplier_name}: all categorized!')
        continue

    name_to_ids = {}
    for p in prods.data:
        name_to_ids.setdefault(p['name'], []).append(p['id'])
    print(f'{supplier_name}: {len(prods.data)} need category, {len(name_to_ids)} unique names', flush=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

    def block(r):
        if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    # Load portal for auth
    try: page.goto(f'{base_url}/portal/search', wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(3)

    fixed = 0
    page_num = 1
    stale = 0

    while name_to_ids and page_num <= 200:
        api_result = page.evaluate('''async (args) => {
            const resp = await fetch(
                `https://mapi.sdspod.com/products/page?size=20&page=${args.page}`,
                { headers: { 'Origin': args.origin } }
            );
            return await resp.json();
        }''', {'page': page_num, 'origin': api_origin})

        items = api_result.get('items', [])
        if not items:
            break

        matched = 0
        for item in items:
            api_name = item.get('name', '')
            if not api_name or api_name not in name_to_ids:
                continue
            matched += 1

            # Get category from API
            cat_name = item.get('categoryName') or item.get('category') or None

            # Try to get from categoryList
            if not cat_name:
                cat_list = item.get('categoryList') or item.get('categorys') or []
                if cat_list:
                    cat_name = ' > '.join([c.get('name','') for c in cat_list if c.get('name')])

            if cat_name:
                for rec_id in name_to_ids[api_name]:
                    try:
                        client.table('products').update({'category': cat_name})\
                            .eq('id', rec_id).execute()
                    except: pass
                fixed += 1

            # Also update product_url if missing
            pid = item.get('id')
            if pid:
                detail_url = f'{base_url}/portal/detail/{pid}'
                for rec_id in name_to_ids[api_name]:
                    try:
                        client.table('products').update({'product_url': detail_url})\
                            .eq('id', rec_id).execute()
                    except: pass

            del name_to_ids[api_name]

        print(f'  P{page_num}: {matched} matched, {len(name_to_ids)} remain', flush=True)

        if matched == 0:
            stale += 1
            if stale >= 5: break
        else:
            stale = 0
        if not name_to_ids: break
        page_num += 1
        time.sleep(0.2)

    print(f'  Fixed: {fixed} categories + URLs, {len(name_to_ids)} remain', flush=True)
    browser.close()
    pw.stop()

print('\nDone!')
