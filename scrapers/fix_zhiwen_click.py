"""Fix 指纹科技 — click each product card from listing to capture SPU URL."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
CHROME_PROFILE = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default'
client = get_client()

prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
print(f'Fake URLs: {len(prods.data)}', flush=True)

pw = sync_playwright().start()
ctx = pw.chromium.launch_persistent_context(
    user_data_dir=CHROME_PROFILE, headless=True,
    args=['--no-sandbox','--disable-gpu'],
    viewport={'width':1920,'height':1080}, locale='zh-CN'
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

fixed = 0
for i, p in enumerate(prods.data):
    name = p['name']
    keyword = name[:20]

    try:
        # Reload clean listing every 50 products
        if i % 50 == 0:
            page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
                      wait_until='domcontentloaded', timeout=20000)
            try: page.wait_for_selector('.product-card', timeout=10000)
            except: pass
            time.sleep(2)

        # Find the search input using JS (bypasses Vue rendering issues)
        found_input = page.evaluate('''() => {
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                const ph = inp.placeholder || '';
                if ((ph.includes('搜索') || ph.includes('搜')) && ph.length > 2) {
                    // Check if visible-ish
                    const rect = inp.getBoundingClientRect();
                    if (rect.width > 100)
                        return true;
                }
            }
            return false;
        }''')

        if not found_input:
            continue

        # Use JS to directly set search and submit
        page.evaluate(f'''() => {{
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {{
                const ph = inp.placeholder || '';
                if ((ph.includes('搜索') || ph.includes('搜')) && ph.length > 2) {{
                    const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    s.call(inp, '{keyword}');
                    inp.dispatchEvent(new Event('input', {{bubbles:true}}));
                    inp.dispatchEvent(new KeyboardEvent('keydown', {{key:'Enter', keyCode:13, bubbles:true}}));
                    inp.dispatchEvent(new KeyboardEvent('keyup', {{key:'Enter', keyCode:13, bubbles:true}}));
                    break;
                }}
            }}
        }}''')
        time.sleep(3)

        # Click first result card
        cards = page.query_selector_all('.product-card')
        if not cards:
            continue

        # Listen for new page
        new_page_ref = [None]
        def on_page(p): new_page_ref[0] = p
        ctx.on('page', on_page)

        # Click card using JS
        cards[0].evaluate('el => { el.dispatchEvent(new MouseEvent("click", {bubbles:true, cancelable:true})); }')
        time.sleep(4)

        ctx.remove_listener('page', on_page)
        new_pg = new_page_ref[0]

        if new_pg and 'spu?id=' in new_pg.url:
            spu_url = new_pg.url
            # Try to get image too
            img_url = None
            try:
                new_pg.wait_for_load_state('domcontentloaded', timeout=5000)
                time.sleep(1)
                imgs = new_pg.query_selector_all('img')
                for img in imgs:
                    src = img.get_attribute('src') or ''
                    if src and ('product' in src or 'hicustom' in src) and 'image-error' not in src and len(src) > 50:
                        img_url = src
                        break
            except: pass

            update = {'product_url': spu_url}
            if img_url: update['image_url'] = img_url
            try:
                client.table('products').update(update).eq('id', p['id']).execute()
                fixed += 1
            except: pass
            new_pg.close()
    except:
        pass

    if (i+1) % 100 == 0:
        total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
        fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
            .like('product_url','%#product=%').execute()
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed, fake={fake.count}', flush=True)

print(f'\nDone: {fixed}', flush=True)
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
    .like('product_url','%#product=%').execute()
print(f'Fake remaining: {fake.count}/{total.count}', flush=True)
ctx.close(); pw.stop()
