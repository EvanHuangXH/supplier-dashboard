"""指纹科技国内 tab — tested approach: wait_for_selector + skip on timeout."""
import sys, os, time, re
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
from bs4 import BeautifulSoup
from common import get_supplier_id, insert_product, log_scrape, get_client

supplier_id = get_supplier_id('指纹科技')
client = get_client()

result = client.table('products').select('id', count='exact').eq('supplier_id', supplier_id).execute()
print(f'DB before: {result.count}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

# Pre-warm: load JIT page first (always works) to bootstrap Vue app
print('Pre-warming via JIT page...', end=' ', flush=True)
try:
    page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
              wait_until='domcontentloaded', timeout=30000)
    page.wait_for_selector('.product-card', timeout=15000)
    print('OK', flush=True)
except:
    print('timeout (continuing anyway)', flush=True)
time.sleep(2)

products = []
seen_names = set()
stale = 0
pn = 1

while pn <= 60:
    url = f'https://www.hicustom.com/productType/allGoods?isSearch=1&page={pn}'
    print(f'P{pn}...', end=' ', flush=True)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
    except PwTimeout:
        print('goto timeout, skip', flush=True)
        stale += 1
        pn += 1
        if stale >= 3: break
        continue

    try:
        page.wait_for_selector('.product-card', state='attached', timeout=15000)
    except PwTimeout:
        print('no cards, skip', flush=True)
        stale += 1
        pn += 1
        if stale >= 3: break
        continue

    # Brief extra wait for images
    time.sleep(2)

    try:
        html = page.content()
    except:
        print('content fail', flush=True)
        stale += 1; pn += 1
        if stale >= 3: break
        continue

    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('.product-card')
    if not cards:
        print('0 cards', flush=True)
        stale += 1; pn += 1
        if stale >= 3: break
        continue

    new_p = 0; img_c = 0
    for card in cards:
        ne = card.select_one('.name')
        if not ne: continue
        name = ne.get_text(strip=True)
        if name in seen_names: continue
        seen_names.add(name); new_p += 1

        price = None
        pnc = card.select_one('.price-num')
        if pnc:
            try: price = float(pnc.get_text(strip=True))
            except: pass

        dd = None
        se = card.select_one('.send')
        if se:
            nums = re.findall(r'(\d+)', se.get_text(strip=True))
            if nums: dd = int(nums[0])

        ie = card.select_one('.product-img')
        img = None
        if ie:
            src = ie.get('src','')
            if src and 'image-error' not in src:
                img = src
                if img.startswith('/'): img = f'https://www.hicustom.com{img}'
                img_c += 1

        products.append({
            'name': name, 'description': None, 'price': price,
            'price_unit': None, 'currency': 'CNY', 'delivery_days': dd,
            'listed_at': None, 'is_hot': bool(card.select_one('.hot-tag')),
            'category': '国内', 'material_tags': [],
            'image_url': img,
            'product_url': f'https://www.hicustom.com/productType/allGoods#product={quote(name, safe="")}',
            'raw': {'supplier': '指纹科技', 'tab': 'domestic'},
        })

    print(f'{new_p}N {len(cards)}C {img_c}I', flush=True)
    stale = 0 if new_p > 0 else stale + 1
    if stale >= 3: break

    if pn % 5 == 0 and products:
        for p in products[-120:]:
            insert_product(supplier_id, p)
        print('  [DB]', flush=True)

    pn += 1

print(f'\nTotal: {len(products)}', flush=True)
nc = 0
for p in products:
    if insert_product(supplier_id, p): nc += 1
log_scrape(supplier_id, len(products), nc, 'success')
print(f'Done: {len(products)} found, {nc} new', flush=True)

r2 = client.table('products').select('id', count='exact').eq('supplier_id', supplier_id).execute()
print(f'DB after: {r2.count}', flush=True)

page.close(); browser.close(); pw.stop()
