"""指纹科技URL修复 - 最终版：断点续传+进程守护+每5页报告"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
PROFILE = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default'
client = get_client()

# Load progress from checkpoint file
CKPT = os.path.join(os.path.dirname(__file__), '.zhiwen_ckpt.json')
done_ids = set()
if os.path.exists(CKPT):
    with open(CKPT) as f:
        done_ids = set(json.load(f))
    print(f'Resuming: {len(done_ids)} already done', flush=True)

# Get products needing fix
prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
name_to_id = {}
for p in prods.data:
    if p['id'] not in done_ids:
        name_to_id[p['name']] = p['id']
print(f'To fix: {len(name_to_id)} (skipped {len(done_ids)} done)', flush=True)

if not name_to_id:
    print('All done!', flush=True)
    exit()

def launch_browser():
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=PROFILE, headless=True,
        args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'],
        viewport={'width':1920,'height':1080}, locale='zh-CN'
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    return pw, ctx, page

pw, ctx, page = launch_browser()

# Pre-load
page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
          wait_until='domcontentloaded', timeout=30000)
try: page.wait_for_selector('.product-card', timeout=15000)
except: pass
time.sleep(2)
print('Session ready', flush=True)

fixed = 0
last_report = time.time()

for tab_label, tab_param in [('JIT', '&tab=jit'), ('国内', '')]:
    for pn in range(1, 200):
        # Restart browser every 5 pages to prevent memory issues
        if pn % 5 == 0 and pn > 1:
            ctx.close()
            pw.stop()
            time.sleep(2)
            pw, ctx, page = launch_browser()
            time.sleep(1)

        url = f'https://www.hicustom.com/productType/allGoods?isSearch=1{tab_param}&page={pn}'
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
        except:
            print(f'  [{tab_label}] P{pn}: goto failed, retrying...', flush=True)
            try:
                pw2, ctx2, page2 = launch_browser()
                pw.stop(); ctx.close()
                pw, ctx, page = pw2, ctx2, page2
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
            except: break

        try: page.wait_for_selector('.product-card', timeout=8000)
        except: break
        time.sleep(2)

        cards = page.query_selector_all('.product-card')
        if not cards: break

        pf = 0
        for card in cards:
            try:
                name_el = card.query_selector('.name')
                if not name_el: continue
                cn = name_el.inner_text().strip()
            except: continue
            if cn not in name_to_id: continue

            # Close all SPU tabs first (cleanup)
            for pg in list(ctx.pages):
                if pg != page and 'spu?id=' in pg.url:
                    try: pg.close()
                    except: pass

            # Click card children
            before = set(ctx.pages)
            for child in card.query_selector_all('*')[:30]:
                try: child.evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true}))')
                except: pass
                time.sleep(0.03)
            time.sleep(3)

            # Find SPU page
            found = False
            for new_pg in ctx.pages:
                if new_pg not in before and 'spu?id=' in new_pg.url:
                    try:
                        client.table('products').update({'product_url': new_pg.url})\
                            .eq('id', name_to_id[cn]).execute()
                        pf += 1; fixed += 1
                        done_ids.add(name_to_id[cn])
                        del name_to_id[cn]
                        found = True
                    except: pass
                    try: new_pg.close()
                    except: pass
                    break
            if not found:
                # Close any new non-SPU tabs
                for new_pg in ctx.pages:
                    if new_pg not in before and new_pg != page:
                        try: new_pg.close()
                        except: pass

            if not name_to_id: break

        # Save checkpoint every page
        with open(CKPT, 'w') as f:
            json.dump(list(done_ids), f)

        now = time.time()
        if now - last_report > 120 or pf > 0:
            total_fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
                .like('product_url','%#product=%').execute()
            print(f'  [{tab_label}] P{pn}: +{pf} | remain={len(name_to_id)} | total_fake={total_fake.count}', flush=True)
            last_report = now

        if not name_to_id: break
        if pf == 0 and pn >= 80: break  # Scan ALL pages

    if not name_to_id: break

print(f'\nDone: {fixed} fixed', flush=True)
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
    .like('product_url','%#product=%').execute()
print(f'Fake remaining: {fake.count}/{total.count}', flush=True)
ctx.close(); pw.stop()
# Clean checkpoint on full completion
if fake.count < 500:
    os.remove(CKPT)
