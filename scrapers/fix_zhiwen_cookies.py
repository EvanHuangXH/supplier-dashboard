"""Fix 指纹科技 URLs using Chrome login session."""
import sys, os, time, re
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
context = pw.chromium.launch_persistent_context(
    user_data_dir=CHROME_PROFILE, headless=True,
    args=['--no-sandbox','--disable-gpu'],
    viewport={'width':1920,'height':1080}, locale='zh-CN',
    timeout=120000  # 2 min timeout for profile loading
)
page = context.pages[0] if context.pages else context.new_page()

page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
          wait_until='domcontentloaded', timeout=30000)
time.sleep(5)

# Check login by looking for visible login dialog
has_modal = page.evaluate('''() => {
    for (const d of document.querySelectorAll('.el-dialog, .el-dialog__wrapper')) {
        if (d.offsetParent !== null) return true;
    }
    return false;
}''')
if has_modal:
    print('Not logged in!', flush=True); context.close(); pw.stop(); exit()

print('Logged in! Starting...', flush=True)

fixed = 0
for i, p in enumerate(prods.data):
    name = p['name'][:25]
    try:
        if i % 30 == 0:
            page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
                      wait_until='domcontentloaded', timeout=30000)
            # Wait for Vue to render cards
            try: page.wait_for_selector('.product-card', timeout=15000)
            except: pass
            time.sleep(2)

        # Find search input - must wait for Vue to render first
        search_input = None
        for inp in page.query_selector_all('input'):
            ph = inp.get_attribute('placeholder') or ''
            if ('搜索' in ph or '搜' in ph) and len(ph) > 2:
                search_input = inp; break
        if not search_input: continue

        # Use native value setter + Vue-compatible events
        search_input.evaluate(f'''el => {{
            const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            s.call(el, '{name}');
            el.dispatchEvent(new Event('input', {{bubbles:true}}));
            el.dispatchEvent(new Event('change', {{bubbles:true}}));
        }}''')
        time.sleep(0.3)
        # Press Enter via the form
        form = search_input.evaluate('el => el.closest("form")')
        if form:
            page.evaluate('''() => {
                const form = document.querySelector('form');
                if (form) form.dispatchEvent(new Event('submit', {bubbles:true, cancelable:true}));
            }''')
        else:
            search_input.evaluate('el => el.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", bubbles:true}))')
        time.sleep(2)

        cards = page.query_selector_all('.product-card')
        if not cards: continue

        new_pg = [None]
        def on_page(p): new_pg[0] = p
        context.on('page', on_page)
        cards[0].evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true}))')
        time.sleep(3)
        context.remove_listener('page', on_page)

        if new_pg[0] and 'spu?id=' in new_pg[0].url:
            spu_url = new_pg[0].url
            img_url = None
            try:
                new_pg[0].wait_for_load_state('domcontentloaded', timeout=5000)
                time.sleep(1)
                img = new_pg[0].query_selector('img[src*=product], img[src*=hicustom], [class*=preview] img')
                if img: img_url = img.get_attribute('src')
            except: pass
            update = {'product_url': spu_url}
            if img_url and 'image-error' not in img_url: update['image_url'] = img_url
            try: client.table('products').update(update).eq('id', p['id']).execute(); fixed += 1
            except: pass
            new_pg[0].close()
    except: pass

    if (i+1) % 100 == 0:
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed', flush=True)

print(f'\nDone: {fixed} URLs', flush=True)
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%#product=%').execute()
print(f'Real URLs: {total.count-fake.count}/{total.count}', flush=True)
context.close(); pw.stop()
