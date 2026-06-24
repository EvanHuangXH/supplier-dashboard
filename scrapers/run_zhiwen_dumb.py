"""最笨方法: 每页每卡片都点开SPU页，读详情名匹配DB"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
PROFILE = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default'
client = get_client()

# Build normalized name lookup for fuzzy matching
prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID).limit(5000).execute()
name_to_id = {}
norm_to_id = {}
for p in prods.data:
    name_to_id[p['name']] = p['id']
    n = re.sub(r'[（(][^）)]*[）)]', '', p['name'])
    n = re.sub(r'\s+', '', n)
    norm_to_id[n] = p['id']
print(f'DB: {len(name_to_id)} names', flush=True)

# Only fix fake URLs
fake_prods = client.table('products').select('id').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
fake_ids = set(p['id'] for p in fake_prods.data)
print(f'Fake URLs: {len(fake_ids)}', flush=True)

pw = sync_playwright().start()
ctx = pw.chromium.launch_persistent_context(
    user_data_dir=PROFILE, headless=True,
    args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'],
    viewport={'width':1920,'height':1080}, locale='zh-CN'
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

fixed = 0
last_report = time.time()

for tab_label, tab_param in [('JIT', '&tab=jit'), ('国内', '')]:
    for pn in range(1, 80):
        # Restart browser every 5 pages
        if pn % 5 == 0 and pn > 1:
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
        pf = 0

        for card in cards:
            # Close old SPU tabs
            for pg in list(ctx.pages):
                if pg != page:
                    try: pg.close()
                    except: pass

            # Click all children to open SPU page
            for child in card.query_selector_all('*')[:30]:
                child.evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true}))')
                time.sleep(0.03)
            time.sleep(3)

            # Check ALL pages for SPU ones
            for spu_pg in ctx.pages:
                if spu_pg == page: continue
                if 'spu?id=' not in spu_pg.url: continue

                # Read product name from SPU detail page
                try:
                    spu_pg.wait_for_load_state('domcontentloaded', timeout=5000)
                    time.sleep(1)
                except: pass

                # Get name from SPU page - try multiple selectors
                detail_name = spu_pg.evaluate('''() => {
                    for (const sel of ['.name', '.product-name', '.goods-name', 'h1', 'h2', '[class*=title]', '.spu-name']) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim().length > 2) return el.textContent.trim();
                    }
                    // Try getting from page title
                    const title = document.title;
                    if (title) return title.split('|')[0].trim();
                    return document.body.innerText.substring(0, 60).trim();
                }''')

                if detail_name:
                    # Try exact match first
                    db_id = name_to_id.get(detail_name)
                    if not db_id:
                        # Try normalized
                        n = re.sub(r'[（(][^）)]*[）)]', '', detail_name)
                        n = re.sub(r'\s+', '', n)
                        db_id = norm_to_id.get(n)

                    if db_id and db_id in fake_ids:
                        try:
                            client.table('products').update({'product_url': spu_pg.url})\
                                .eq('id', db_id).execute()
                            pf += 1; fixed += 1
                            fake_ids.discard(db_id)
                        except: pass
                break  # Only process first SPU page per card

        now = time.time()
        if now - last_report > 60 or pf > 0:
            print(f'  [{tab_label}] P{pn}: +{pf} | remain={len(fake_ids)}', flush=True)
            last_report = now

        if not fake_ids: break
        if pf == 0 and pn >= 10: break

    if not fake_ids: break

print(f'\nDone: {fixed}', flush=True)
ctx.close(); pw.stop()
