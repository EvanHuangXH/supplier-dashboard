"""Fix images for 指纹科技 JIT products — re-scrape all JIT pages and update image_url."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
from bs4 import BeautifulSoup
from common import get_supplier_id, get_client

supplier_id = get_supplier_id('指纹科技')
client = get_client()

# Count products needing fix
bad = client.table('products').select('id', count='exact').eq('supplier_id', supplier_id)\
    .or_('image_url.is.null,image_url.ilike.%image-error%').execute()
print(f'Products needing image fix: {bad.count}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

fixed = 0
pn = 1
stale = 0

while pn <= 30:
    url = f'https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page={pn}'
    print(f'JIT P{pn}...', end=' ', flush=True)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
    except PwTimeout:
        print('goto timeout', flush=True)
        stale += 1; pn += 1
        if stale >= 3: break
        continue

    try:
        page.wait_for_selector('.product-card', timeout=15000)
    except PwTimeout:
        print('no cards', flush=True)
        break

    time.sleep(2)
    try:
        html = page.content()
    except:
        print('content fail', flush=True)
        break

    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('.product-card')
    if not cards: break

    page_fixed = 0
    for card in cards:
        ne = card.select_one('.name')
        if not ne: continue
        name = ne.get_text(strip=True)

        ie = card.select_one('.product-img')
        img = None
        if ie:
            src = ie.get('src','')
            if src and 'image-error' not in src:
                img = src
                if img.startswith('/'): img = f'https://www.hicustom.com{img}'
        if not img: continue

        # Find and update product by name (JIT products use name-based URL)
        from urllib.parse import quote
        product_url = f'https://www.hicustom.com/productType/allGoods#product={quote(name, safe="")}'

        # Update image in DB directly
        result = client.table('products').select('id,image_url')\
            .eq('supplier_id', supplier_id).eq('product_url', product_url).execute()
        if result.data:
            existing_img = result.data[0].get('image_url','')
            if not existing_img or 'image-error' in (existing_img or ''):
                client.table('products').update({'image_url': img})\
                    .eq('id', result.data[0]['id']).execute()
                page_fixed += 1

    print(f'{page_fixed} fixed, {len(cards)} cards', flush=True)
    fixed += page_fixed
    if page_fixed == 0:
        stale += 1
        if stale >= 3: break
    else:
        stale = 0
    pn += 1

print(f'\nTotal fixed: {fixed}', flush=True)

bad2 = client.table('products').select('id', count='exact').eq('supplier_id', supplier_id)\
    .or_('image_url.is.null,image_url.ilike.%image-error%').execute()
print(f'Remaining bad images: {bad2.count}', flush=True)

page.close(); browser.close(); pw.stop()
