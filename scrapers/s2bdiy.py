"""Scraper for s2bdiy.com — API-based via /req/frontend/basicProduct."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client, log_scrape, get_supplier_id

BASE_URL = 'https://s2bdiy.com'
API_URL = 'https://s2bdiy.com/req/frontend/basicProduct'
SUPPLIER_NAME = 'S2BDIY'


def scrape():
    client = get_client()

    # Register supplier if needed
    r = client.table('suppliers').select('id').eq('name', SUPPLIER_NAME).execute()
    if r.data:
        supplier_id = r.data[0]['id']
    else:
        result = client.table('suppliers').insert({
            'name': SUPPLIER_NAME,
            'website': BASE_URL,
            'shipping_from': '福建',
            'status': 'active'
        }).execute()
        supplier_id = result.data[0]['id']
    print(f'Supplier ID: {supplier_id}', flush=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    page.goto(f'{BASE_URL}/products', wait_until='networkidle', timeout=60000)
    time.sleep(3)

    all_products = []
    pn = 1
    stale = 0
    total_pages = None

    while pn <= 500:
        result = page.evaluate('''async (args) => {
            const resp = await fetch(
                `https://s2bdiy.com/req/frontend/basicProduct?page=${args.page}&page_size=48&zone=cn`
            );
            return await resp.json();
        }''', {'page': pn})

        data = result.get('data', {})
        items = data.get('data', [])
        if total_pages is None:
            total_pages = data.get('last_page', 999)
        if not items:
            break
        if total_pages == 999 and pn == 1:
            total = data.get('total', 0)
            total_pages = (total // 20) + 1 if total else 999

        batch = []
        for item in items:
            pid = item.get('id')
            code = item.get('code', '')
            name = item.get('name', '')
            if not name:
                continue

            price = None
            try: price = float(item.get('purchase_price', 0))
            except: pass

            image_url = item.get('view_image_src') or item.get('design_product_image') or ''
            category = item.get('category_name') or None
            material = item.get('product_material') or ''
            material_tags = [material] if material else []
            is_new = item.get('is_new') == 1
            is_hot = item.get('is_hot_sell') == 1
            delivery_text = item.get('deliver_goods_text') or ''
            delivery_days = None
            import re
            nums = re.findall(r'(\d+)', delivery_text)
            if nums:
                dd = int(nums[0])
                delivery_days = dd if dd > 0 else None

            product_url = f'{BASE_URL}/products/{pid}'

            batch.append({
                'name': name,
                'description': None,
                'price': price,
                'price_unit': None,
                'currency': 'CNY',
                'delivery_days': delivery_days,
                'listed_at': None,
                'is_hot': is_hot,
                'is_new': is_new,
                'category': category,
                'material_tags': material_tags,
                'image_url': image_url,
                'product_url': product_url,
                'raw': {'supplier': SUPPLIER_NAME, 'code': code},
            })

        # Insert to DB
        from common import insert_product
        for p in batch:
            insert_product(supplier_id, p)

        all_products.extend(batch)
        print(f'  P{pn}: {len(batch)} items | total={len(all_products)}/{total_pages} pages', flush=True)

        if pn >= total_pages or len(items) == 0:
            break

        pn += 1
        time.sleep(0.3)

    log_scrape(supplier_id, len(all_products), sum(1 for p in all_products if p.get('_new', True)), 'success')
    print(f'Done: {len(all_products)} products', flush=True)
    browser.close(); pw.stop()


if __name__ == '__main__':
    scrape()
