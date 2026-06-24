"""Fix sdspod detail URLs via mapi.sdspod.com API (with browser auth cookies)."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

client = get_client()

SITES = [
    # (name, base_url, supplier_id, api_origin)
    ('海天城', 'http://www.htccustom.com', 2, 'http://www.htccustom.com'),
    ('艺之冠', 'http://ykartwood.com', 3, 'http://ykartwood.com'),
    ('SDS', 'https://www.sdsdiy.com', 6, 'https://www.sdsdiy.com'),
    ('极特', 'http://www.podjit.com', 11, 'http://www.podjit.com'),
]

for supplier_name, base_url, sid, api_origin in SITES:
    # Get products lacking detail URLs
    prods = client.table('products').select('id,name').eq('supplier_id', sid)\
        .not_.like('product_url', '%/detail/%').limit(5000).order('id').execute()
    if not prods.data:
        print(f'{supplier_name}: all done!')
        continue

    # name → list of ids
    name_to_ids = {}
    for p in prods.data:
        name_to_ids.setdefault(p['name'], []).append(p['id'])
    print(f'{supplier_name}: {len(prods.data)} products, {len(name_to_ids)} unique names', flush=True)

    # Build normalized name index for fuzzy matching
    import unicodedata as _uc
    def _norm(n):
        n = _uc.normalize('NFKC', n)
        n = re.sub(r'\s+', '', n)
        n = re.sub(r'[（(][^）)]*[）)]', '', n)
        return n.lower()
    normalized_ids = {}
    for name, ids in name_to_ids.items():
        nname = _norm(name)
        if nname not in normalized_ids:
            normalized_ids[nname] = []
        normalized_ids[nname].extend(ids)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

    def block(r):
        if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    # Load portal page for auth cookies
    url = f'{base_url}/portal/search'
    print(f'  Loading {url} for auth...', flush=True)
    try: page.goto(url, wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(3)

    fixed = 0
    page_num = 1
    stale = 0

    while name_to_ids and page_num <= 200:
        # Call product API from within browser context (has auth cookies)
        api_result = page.evaluate('''async (args) => {
            const resp = await fetch(
                `https://mapi.sdspod.com/products/page?size=20&page=${args.page}`,
                { headers: { 'Origin': args.origin, 'Referer': args.origin + '/portal/search' } }
            );
            return await resp.json();
        }''', {'page': page_num, 'origin': api_origin})

        items = api_result.get('items', [])
        if not items:
            print(f'  P{page_num}: no items', flush=True)
            break

        matched = 0
        for item in items:
            api_name = item.get('name', '')
            if not api_name:
                continue
            pid = item.get('id')
            if not pid:
                continue
            detail_url = f'{base_url}/portal/detail/{pid}'

            # Pass 1: exact match
            if api_name in name_to_ids:
                for rec_id in name_to_ids[api_name]:
                    try:
                        client.table('products').update({'product_url': detail_url}).eq('id', rec_id).execute()
                    except: pass
                del name_to_ids[api_name]
                matched += 1; fixed += 1
                continue

            # Pass 2: normalized match
            nname = _norm(api_name)
            if nname in normalized_ids:
                for rec_id in normalized_ids[nname]:
                    try:
                        client.table('products').update({'product_url': detail_url}).eq('id', rec_id).execute()
                    except: pass
                # Remove from both lookups
                for name in list(name_to_ids.keys()):
                    if _norm(name) == nname:
                        del name_to_ids[name]
                matched += 1; fixed += 1

        print(f'  P{page_num}: {matched} matched, {len(name_to_ids)} remain', flush=True)

        if not name_to_ids:
            break
        if matched == 0:
            stale += 1
            if stale >= 5:
                print(f'  5 stale pages, stopping', flush=True)
                break
        else:
            stale = 0

        if not name_to_ids:
            print(f'  All matched!', flush=True)
            break

        page_num += 1
        time.sleep(0.3)

    print(f'  Final: {fixed} URLs updated, {len(name_to_ids)} remain', flush=True)
    browser.close()
    pw.stop()

# Report
print()
for sid, name in [(2,'海天城'),(3,'艺之冠'),(6,'SDS'),(11,'极特')]:
    total = client.table('products').select('id', count='exact').eq('supplier_id', sid).execute()
    with_d = client.table('products').select('id', count='exact').eq('supplier_id', sid)\
        .like('product_url', '%/detail/%').execute()
    print(f'{name}: {with_d.count}/{total.count} detail URLs')
