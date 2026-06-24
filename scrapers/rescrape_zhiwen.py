"""重抓指纹科技 — 翻列表页+点卡取SPU链接+读卡名价图，去重入库"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client, insert_product

SUPPLIER_ID = 5
PROFILE = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default'
client = get_client()

# Checkpoint
CKPT = os.path.join(os.path.dirname(__file__), '.zhiwen_rescrape.json')
done_pages = set()
if os.path.exists(CKPT):
    import json
    with open(CKPT) as f:
        done_pages = set(json.load(f))
    print(f'Resuming: {len(done_pages)} pages done', flush=True)

pw = sync_playwright().start()
ctx = pw.chromium.launch_persistent_context(
    user_data_dir=PROFILE, headless=True,
    args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'],
    viewport={'width':1920,'height':1080}, locale='zh-CN'
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

total_new = 0
total_updated = 0

for tab_label, tab_param in [('JIT', '&tab=jit'), ('国内', '')]:
    for pn in range(1, 200):
        page_key = f'{tab_label}_{pn}'
        if page_key in done_pages:
            continue

        # Restart browser every 10 pages
        if pn % 10 == 0 and pn > 1:
            ctx.close(); pw.stop(); time.sleep(2)
            pw = sync_playwright().start()
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=PROFILE, headless=True,
                args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'],
                viewport={'width':1920,'height':1080}, locale='zh-CN'
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

        url = f'https://www.hicustom.com/productType/allGoods?isSearch=1{tab_param}&page={pn}'
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
        except: break
        try: page.wait_for_selector('.product-card', timeout=8000)
        except: break
        time.sleep(2)

        cards = page.query_selector_all('.product-card')
        if not cards: break

        pn_new = 0
        pn_update = 0
        for card in cards:
            try:
                name_el = card.query_selector('.name')
                if not name_el: continue
                cn = name_el.inner_text().strip()
            except: continue

            # Get price from card
            price = None
            try:
                price_el = card.query_selector('.price-num, [class*=price]')
                if price_el:
                    nums = re.findall(r'[\d.]+', price_el.inner_text())
                    if nums:
                        try: price = float(nums[0])
                        except: pass
            except: pass

            # Get image
            img_url = None
            try:
                img_el = card.query_selector('img, [class*=product-img] img')
                if img_el:
                    img_url = img_el.get_attribute('src') or img_el.get_attribute('data-src') or ''
            except: pass

            # Click to get SPU URL
            for pg in list(ctx.pages):
                if pg != page:
                    try: pg.close()
                    except: pass

            before = set(ctx.pages)
            for child in card.query_selector_all('*')[:30]:
                try: child.evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true}))')
                except: pass
                time.sleep(0.03)
            time.sleep(3)

            spu_url = None
            for new_pg in ctx.pages:
                if new_pg not in before and 'spu?id=' in new_pg.url:
                    spu_url = new_pg.url
                    try: new_pg.close()
                    except: pass
                    break

            if not spu_url:
                continue

            # Check DB for existing product by name
            existing = client.table('products').select('id,product_url').eq('supplier_id', SUPPLIER_ID).eq('name', cn).execute()

            if existing.data:
                old_url = existing.data[0].get('product_url', '')
                if '#product=' in old_url or old_url != spu_url:
                    update = {'product_url': spu_url}
                    if price: update['price'] = price
                    if img_url and 'image-error' not in img_url: update['image_url'] = img_url
                    try:
                        client.table('products').update(update).eq('id', existing.data[0]['id']).execute()
                        pn_update += 1
                    except: pass
            else:
                # New product
                data = {
                    'name': cn, 'description': None, 'price': price,
                    'price_unit': None, 'currency': 'CNY', 'delivery_days': None,
                    'listed_at': None, 'is_hot': False,
                    'category': '海外' if tab_label == 'JIT' else '国内',
                    'material_tags': [], 'image_url': img_url,
                    'product_url': spu_url,
                    'raw': {'supplier': '指纹科技'},
                }
                insert_product(SUPPLIER_ID, data)
                pn_new += 1

        total_new += pn_new
        total_updated += pn_update
        done_pages.add(page_key)

        # Save checkpoint
        import json
        with open(CKPT, 'w') as f:
            json.dump(list(done_pages), f)

        if pn_new > 0 or pn_update > 0 or pn % 5 == 0:
            fake_count = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
                .like('product_url','%#product=%').execute()
            print(f'  [{tab_label}] P{pn}: +{pn_new}N +{pn_update}U | fake={fake_count.count}', flush=True)

        if pn_new == 0 and pn_update == 0 and pn >= 10:
            break

    if pn_new == 0 and pn_update == 0 and pn >= 10:
        continue

print(f'\nDone: {total_new} new, {total_updated} updated', flush=True)
t = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
f = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%#product=%').execute()
print(f'Fake remaining: {f.count}/{t.count}', flush=True)
ctx.close(); pw.stop()
