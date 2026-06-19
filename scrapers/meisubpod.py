"""Scraper for 美可印 (meisubpod.com) — API-based via /mkyserver/system/."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client, log_scrape

BASE_URL = 'https://meisubpod.com'
API_BASE = f'{BASE_URL}/mkyserver'
SUPPLIER_NAME = '美可印'


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

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
    time.sleep(5)
    el = page.query_selector('text=产品中心')
    if el: el.click(); time.sleep(5)

    # Get category code→name mapping
    cats_result = page.evaluate(f'fetch("{API_BASE}/system/findClassifyList").then(r=>r.json())')
    cat_map = {c['code']: c['name'] for c in cats_result.get('classifyList', [])}
    print(f'Categories: {len(cat_map)}', flush=True)

    # Get all products
    prod_result = page.evaluate(f'fetch("{API_BASE}/system/findProductCenter").then(r=>r.json())')
    products = prod_result.get('productList', [])
    print(f'Products from API: {len(products)}', flush=True)

    from common import insert_product
    all_products = []
    for i, item in enumerate(products):
        name = item.get('chineseName') or item.get('spuName') or ''
        if not name: continue

        image = item.get('image') or item.get('custom1') or ''
        if image and not image.startswith('http'):
            image = f'{API_BASE}/{image}'

        cat_code = item.get('classify1') or ''
        category = cat_map.get(cat_code) or None

        spu_code = item.get('spuCode') or ''
        product_url = f'{BASE_URL}/?spu={spu_code}' if spu_code else BASE_URL

        # Try to get price from detail API (every 10th product to save time)
        price = None
        if i % 10 == 0 or i < 5:
            try:
                detail = page.evaluate(f'fetch("{API_BASE}/system/asyncFindProductCenterDetail?spuCode={spu_code}").then(r=>r.json())')
                min_p = detail.get('minPrice')
                if min_p: price = float(min_p)
            except: pass

        factory = item.get('factoryName') or ''
        site = item.get('siteName') or ''
        desc = item.get('commodityDesc') or ''
        currency_map = {'美元': 'USD', '欧元': 'EUR', '人民币': 'CNY', '英镑': 'GBP', '澳元': 'AUD', '加元': 'CAD', '日元': 'JPY'}
        currency = currency_map.get(item.get('currencyName') or '', 'CNY')

        product = {
            'name': name, 'description': desc or None, 'price': price,
            'price_unit': None, 'currency': currency,
            'delivery_days': None, 'listed_at': None,
            'is_hot': False, 'is_new': False,
            'category': category,
            'material_tags': [], 'image_url': image,
            'product_url': product_url,
            'raw': {'supplier': SUPPLIER_NAME, 'factory': factory, 'site': site},
        }
        all_products.append(product)

    # Batch insert
    nc = 0
    for p in all_products:
        if insert_product(supplier_id, p):
            nc += 1
        # Also get prices for remaining products
        if p['price'] is None:
            spu = p.get('raw', {}).get('spuCode', '') or p.get('product_url', '').split('spu=')[-1]
            if spu:
                try:
                    detail = page.evaluate(f'fetch("{API_BASE}/system/asyncFindProductCenterDetail?spuCode={spu}").then(r=>r.json())')
                    min_p = detail.get('minPrice')
                    if min_p:
                        price_val = float(min_p)
                        client.table('products').update({'price': price_val}).eq('supplier_id', supplier_id).eq('name', p['name']).execute()
                        p['price'] = price_val
                except: pass

    log_scrape(supplier_id, len(all_products), nc, 'success')
    print(f'Done: {len(all_products)} products, {nc} new', flush=True)
    browser.close(); pw.stop()


if __name__ == '__main__':
    scrape()
