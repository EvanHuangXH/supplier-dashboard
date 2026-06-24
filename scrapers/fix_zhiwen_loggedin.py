"""Fix 指纹科技 URLs — login + search → click card → capture SPU URL."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
USER = 'lanlijian'
PASS = 'lanlijian@123456'
client = get_client()

prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
print(f'Fake URLs to fix: {len(prods.data)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
context = browser.new_context(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
page = context.new_page()

# Step 1: Login
print('Logging in...', flush=True)
page.goto('https://www.hicustom.com/login', wait_until='networkidle', timeout=60000)
time.sleep(3)

# Fill login form
for sel in ['input[placeholder*=用户名]', 'input[placeholder*=手机]', 'input[placeholder*=邮箱]', 'input[type=text]']:
    user_input = page.query_selector(sel)
    if user_input:
        user_input.fill(USER)
        break

pass_input = page.query_selector('input[type=password]')
if pass_input:
    pass_input.fill(PASS)

# Click login button
login_btn = page.query_selector('button:has-text("登录"), button:has-text("登錄"), button[type=submit]')
if login_btn:
    login_btn.click()
    time.sleep(5)
    print(f'After login URL: {page.url}', flush=True)
else:
    # Try pressing Enter
    pass_input.press('Enter') if pass_input else None
    time.sleep(5)

# Check if logged in (should redirect to home or stay)
print(f'Logged in: {"login" not in page.url.lower()}', flush=True)

# Step 2: For each product, search and capture SPU URL
fixed = 0
seen_spu = set()

for i, p in enumerate(prods.data):
    name = p['name']
    keyword = name[:25]  # Short search term

    try:
        # Reload listing page periodically to stay fresh
        if i % 30 == 0:
            page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
                      wait_until='networkidle', timeout=30000)
            time.sleep(2)

        # Type search and submit
        search_input = page.query_selector('input[placeholder*=搜索]')
        if not search_input:
            for inp in page.query_selector_all('input'):
                ph = inp.get_attribute('placeholder') or ''
                if '搜索' in ph or '搜' in ph:
                    if inp.bounding_box():
                        search_input = inp
                        break
        if not search_input:
            continue

        search_input.evaluate(f'el => {{ el.value = "{keyword}"; el.dispatchEvent(new Event("input", {{bubbles:true}})); }}')
        time.sleep(0.3)
        search_input.evaluate('el => el.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", keyCode:13, bubbles:true}))')
        time.sleep(2)

        # Click first card
        cards = page.query_selector_all('.product-card')
        if not cards:
            continue

        new_page_ref = [None]
        def on_page(p):
            new_page_ref[0] = p
        context.on('page', on_page)

        cards[0].evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true, cancelable:true}))')
        time.sleep(3)

        context.remove_listener('page', on_page)
        new_page = new_page_ref[0]

        if new_page and 'spu?id=' in new_page.url:
            spu_url = new_page.url
            # Also capture image from detail page
            img_url = None
            try:
                new_page.wait_for_load_state('domcontentloaded', timeout=5000)
                time.sleep(1)
                img = new_page.query_selector('img[src*=product], img[src*=hicustom], .product-img img, [class*=preview] img')
                if img:
                    img_url = img.get_attribute('src')
            except: pass

            update = {'product_url': spu_url}
            if img_url and 'image-error' not in img_url:
                update['image_url'] = img_url

            try:
                client.table('products').update(update).eq('id', p['id']).execute()
                fixed += 1
            except: pass
            seen_spu.add(spu_url)
            new_page.close()

    except Exception as e:
        pass

    if (i + 1) % 100 == 0:
        remain = len(prods.data) - i - 1
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed, {remain} remain', flush=True)

print(f'\nDone: {fixed} URLs updated', flush=True)

total = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').execute()
bad_img = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID)\
    .or_('image_url.is.null,image_url.ilike.%image-error%').execute()
print(f'指纹科技: {total.count-fake.count}/{total.count} real URLs, {bad_img.count} bad images', flush=True)

browser.close(); pw.stop()
