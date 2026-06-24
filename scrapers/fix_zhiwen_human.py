"""Fix 指纹科技 URLs — simulate human: search → click card → capture SPU URL."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
client = get_client()

prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
print(f'Fake URLs to fix: {len(prods.data)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
context = browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
page = context.new_page()

# Load the listing for cookies/auth
page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
          wait_until='networkidle', timeout=60000)
time.sleep(3)

fixed = 0
seen_urls = set()

for i, p in enumerate(prods.data):
    name = p['name']
    short_name = name[:30]  # Search with shorter name for better matching

    try:
        # Reload clean page every 20 products to avoid state issues
        if i % 20 == 0:
            page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
                      wait_until='networkidle', timeout=30000)
            time.sleep(3)

        # Find search input fresh each time
        search_input = None
        for inp in page.query_selector_all('input'):
            ph = inp.get_attribute('placeholder') or ''
            if '搜索' in ph or 'search' in ph.lower():
                search_input = inp
                break
        if not search_input:
            search_input = page.query_selector('.el-input__inner')

        if not search_input:
            continue

        # Use JS to force clear and type (bypass visibility checks)
        search_input.evaluate(f'el => {{ el.value = ""; el.dispatchEvent(new Event("input", {{bubbles:true}})); }}')
        search_input.evaluate(f'el => {{ el.value = "{short_name}"; el.dispatchEvent(new Event("input", {{bubbles:true}})); }}')
        time.sleep(0.3)
        search_input.evaluate('el => el.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", keyCode:13, bubbles:true}))')
        time.sleep(3)

        # Click first product card and capture new page
        cards = page.query_selector_all('.product-card')
        if not cards:
            continue

        new_page_ref = [None]
        def on_page(p):
            new_page_ref[0] = p
        context.on('page', on_page)

        # JS force click first card's image/content
        click_target = cards[0].query_selector('.product-img-content, .product-img, img') or cards[0]
        click_target.evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true, cancelable:true}))')
        time.sleep(3)

        context.remove_listener('page', on_page)
        new_page = new_page_ref[0]

        if new_page:
            spu_url = new_page.url
            if 'spu?id=' in spu_url:
                # Update DB
                try:
                    client.table('products').update({'product_url': spu_url})\
                        .eq('id', p['id']).execute()
                    fixed += 1
                except: pass

                # Also try to capture image from the new page
                try:
                    new_page.wait_for_load_state('domcontentloaded', timeout=5000)
                    time.sleep(1)
                    img = new_page.query_selector('img[src*=product], img[src*=hicustom], .product-img img')
                    if img:
                        img_url = img.get_attribute('src')
                        if img_url and 'image-error' not in img_url:
                            client.table('products').update({'image_url': img_url})\
                                .eq('id', p['id']).execute()
                except: pass

            new_page.close()

    except Exception as e:
        pass

    if (i + 1) % 50 == 0:
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed', flush=True)

print(f'\nDone: {fixed} URLs updated', flush=True)

# Check result
total = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').execute()
print(f'指纹科技: {total.count-fake.count}/{total.count} real URLs', flush=True)

browser.close(); pw.stop()
