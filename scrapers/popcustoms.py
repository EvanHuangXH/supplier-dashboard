"""Scraper for popcustoms.cn — API-based via i.popcustoms.cn/api/v1/search."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client, log_scrape

BASE_URL = 'https://www.popcustoms.cn'
API_URL = 'https://i.popcustoms.cn/api/v1/search'
SUPPLIER_NAME = 'Popcustoms'


def scrape():
    client = get_client()

    # Register supplier
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

    # Scrape both domestic and overseas
    all_products = []
    for shipping_filter, ship_label in [(1, '国内发货'), (0, '海外发货')]:
        pn = 1
        stale = 0
        print(f'\n[{ship_label}]', flush=True)

        while pn <= 500:
            result = page.evaluate('''async (args) => {
                const resp = await fetch(
                    `https://i.popcustoms.cn/api/v1/search?type=basics&page=${args.page}&limit=48&is_ship_from_china=${args.ship}`
                );
                return await resp.json();
            }''', {'page': pn, 'ship': shipping_filter})

            items = result.get('data', [])
            meta = result.get('meta', {})
            total_pages = meta.get('last_page', 999)
            total_items = meta.get('total', 0)

            if not items:
                break

            batch = []
            for item in items:
                pid = item.get('id')
                code = item.get('code', '')
                name = item.get('name', '')
                if not name:
                    continue

                image_url = item.get('thumb') or item.get('cover') or ''
                material = item.get('material') or ''
                material_tags = [material] if material else []
                technique = item.get('technique') or ''
                if technique:
                    material_tags.append(technique)

                is_hot = item.get('is_hot', False)
                is_new = item.get('is_new', False)
                manufacturer = item.get('manufacturer', {})
                shipping_from = manufacturer.get('shipping_from_name') or manufacturer.get('shipping_from') or None

                product_url = f'{BASE_URL}/products/{pid}'

                batch.append({
                    'name': name,
                    'description': item.get('en_name'),
                    'price': None,
                    'price_unit': None,
                    'currency': 'CNY',
                    'delivery_days': None,
                    'listed_at': None,
                    'is_hot': is_hot,
                    'is_new': is_new,
                    'category': ship_label,
                    'material_tags': material_tags,
                    'image_url': image_url,
                    'product_url': product_url,
                    'raw': {'supplier': SUPPLIER_NAME, 'code': code, 'shipping': shipping_from},
                })

            from common import insert_product
            for p in batch:
                insert_product(supplier_id, p)

            all_products.extend(batch)
            print(f'  P{pn}: {len(batch)} items | total={len(all_products)}/{total_items}', flush=True)

            if pn >= total_pages or len(items) < 48:
                break

            pn += 1
            time.sleep(0.3)

    log_scrape(supplier_id, len(all_products), 0, 'success')
    print(f'\nDone: {len(all_products)} products', flush=True)
    browser.close(); pw.stop()


if __name__ == '__main__':
    scrape()
