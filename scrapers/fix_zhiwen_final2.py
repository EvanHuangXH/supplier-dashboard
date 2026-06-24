"""Fix 指纹科技 — search+click per product, capture SPU by counting tabs."""
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
    name = p['name'][:25].replace("'", "").replace('"', "").replace('\\', '')
    try:
        # Reload clean listing every 30 products
        if i % 30 == 0:
            page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
                      wait_until='domcontentloaded', timeout=20000)
            try: page.wait_for_selector('.product-card', timeout=10000)
            except: pass
            time.sleep(2)

        # JS: find search input, fill, submit
        page.evaluate(f'''() => {{
            for (const inp of document.querySelectorAll('input')) {{
                if ((inp.placeholder||'').includes('搜索')) {{
                    const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    s.call(inp, '{name}');
                    inp.dispatchEvent(new Event('input', {{bubbles:true}}));
                    inp.dispatchEvent(new KeyboardEvent('keydown', {{key:'Enter', bubbles:true}}));
                    break;
                }}
            }}
        }}''')
        time.sleep(3)

        cards = page.query_selector_all('.product-card')
        if not cards: continue

        # Count existing pages, click all card children to trigger SPU page
        existing_pages = set(ctx.pages)
        card = cards[0]
        children = card.query_selector_all('*')
        for child in children[:30]:  # first 30 children
            child.evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true}))')
            time.sleep(0.05)
        time.sleep(4)

        new_pages = [p for p in ctx.pages if p not in existing_pages]
        for new_pg in new_pages:
            if 'spu?id=' in new_pg.url:
                spu_url = new_pg.url
                try:
                    client.table('products').update({'product_url': spu_url}).eq('id', p['id']).execute()
                    fixed += 1
                except: pass
                new_pg.close()
                break  # Use first valid SPU page
    except: pass

    if (i+1) % 50 == 0:
        total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
        fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
            .like('product_url','%#product=%').execute()
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed, {fake.count} fake remain', flush=True)

print(f'\nDone: {fixed}', flush=True)
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
    .like('product_url','%#product=%').execute()
print(f'Fake: {fake.count}/{total.count}', flush=True)
ctx.close(); pw.stop()
