"""Scraper for 紫元素 (zi321.com) — intercept API response during page load."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client, log_scrape

BASE_URL = 'https://zi321.com'
SUPPLIER_NAME = '紫元素'


def scrape():
    client = get_client()
    r = client.table('suppliers').select('id').eq('name', SUPPLIER_NAME).execute()
    if r.data:
        supplier_id = r.data[0]['id']
    else:
        supplier_id = client.table('suppliers').insert({
            'name': SUPPLIER_NAME, 'website': BASE_URL, 'shipping_from': '福建', 'status': 'active'
        }).execute().data[0]['id']
    print(f'Supplier ID: {supplier_id}', flush=True)

    # Capture API data during page load
    api_responses = []

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

    def on_resp(resp):
        if 'merchantapi.rouhuipod.com/api/v1/product' in resp.url:
            try:
                data = resp.json()
                if data.get('code') == 1:
                    api_responses.append(data)
                    print(f'  Captured API: {resp.url[:150]}', flush=True)
            except: pass

    page.on('response', on_resp)

    print('Loading page...', flush=True)
    try: page.goto(f'{BASE_URL}/template/productList', wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(8)

    all_products = []
    seen_ids = set()

    for data in api_responses:
        list_data = data.get('data', {})
        items = list_data.get('list', [])
        total = list_data.get('total', 0)
        print(f'API: {len(items)} items, {total} total', flush=True)

        for item in items:
            pid = item.get('id')
            if not pid or pid in seen_ids: continue
            seen_ids.add(pid)

            name = item.get('name') or ''
            if not name: continue

            # Extract price from item
            price = None
            for pf in ['price', 'min_price', 'sale_price']:
                if item.get(pf):
                    try: price = float(item[pf]); break
                    except: pass

            img = item.get('image') or item.get('main_image') or item.get('cover') or ''
            cat = item.get('category_name') or None

            all_products.append({
                'name': name, 'description': item.get('en_name'),
                'price': price, 'price_unit': None, 'currency': 'CNY',
                'delivery_days': None, 'listed_at': None,
                'is_hot': False, 'category': cat,
                'material_tags': [], 'image_url': img,
                'product_url': f'{BASE_URL}/template/productDetail?id={pid}',
                'raw': {'supplier': SUPPLIER_NAME, 'code': item.get('code','')},
            })

    # If only got 50, paginate via the page's own scroll mechanism
    if len(all_products) < 300:
        print(f'  Only {len(all_products)} from API, trying page scrape...', flush=True)
        # Scroll el-scrollbar to load more
        for i in range(30):
            page.evaluate('''() => {
                const c = document.querySelector('.el-scrollbar__wrap');
                if (c) c.scrollTop += 600;
            }''')
            time.sleep(0.6)

        body = page.evaluate('() => document.body.innerText')
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        i = 0
        while i < len(lines) - 1:
            line = lines[i]
            nxt = lines[i+1] if i+1 < len(lines) else ''
            pm = re.match(r'[¥￥]\s*(\d+\.?\d{0,2})\s*[~\-]\s*[¥￥]?\s*(\d+\.?\d{0,2})', nxt)
            sp = re.match(r'[¥￥]\s*(\d+\.?\d{0,2})$', nxt) if not pm else None
            if pm and len(line) > 3 and len(line) < 200 and line not in seen_ids:
                seen_ids.add(line)
                price = (float(pm.group(1)) + float(pm.group(2))) / 2
                all_products.append({
                    'name': line, 'description': None, 'price': round(price,2),
                    'price_unit': None, 'currency': 'CNY', 'delivery_days': None,
                    'listed_at': None, 'is_hot': False, 'category': None,
                    'material_tags': [], 'image_url': None,
                    'product_url': f'{BASE_URL}/template/productList',
                    'raw': {'supplier': SUPPLIER_NAME},
                })
                i += 2; continue
            elif sp and len(line) > 3 and len(line) < 200 and line not in seen_ids:
                seen_ids.add(line)
                all_products.append({
                    'name': line, 'description': None, 'price': float(sp.group(1)),
                    'price_unit': None, 'currency': 'CNY', 'delivery_days': None,
                    'listed_at': None, 'is_hot': False, 'category': None,
                    'material_tags': [], 'image_url': None,
                    'product_url': f'{BASE_URL}/template/productList',
                    'raw': {'supplier': SUPPLIER_NAME},
                })
                i += 2; continue
            i += 1

    from common import insert_product
    nc = 0
    for p in all_products:
        if insert_product(supplier_id, p): nc += 1

    log_scrape(supplier_id, len(all_products), nc, 'success')
    print(f'Done: {len(all_products)} found, {nc} new', flush=True)
    browser.close(); pw.stop()


if __name__ == '__main__':
    scrape()
