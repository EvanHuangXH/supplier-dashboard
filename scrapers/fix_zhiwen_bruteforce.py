"""Fix 指纹科技 — paginate JIT+domestic listing, click cards, capture SPU URL."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
CHROME_PROFILE = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default'
client = get_client()

prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID).limit(5000).execute()
name_to_id = {}
for p in prods.data:
    name_to_id[p['name']] = p['id']
print(f'DB names: {len(name_to_id)}', flush=True)

pw = sync_playwright().start()
ctx = pw.chromium.launch_persistent_context(
    user_data_dir=CHROME_PROFILE, headless=True,
    args=['--no-sandbox','--disable-gpu'],
    viewport={'width':1920,'height':1080}, locale='zh-CN'
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

fixed = 0
# Try both tabs
for tab_label, tab_param in [('JIT', '&tab=jit'), ('国内', '')]:
    print(f'\n[{tab_label}]', flush=True)
    for pn in range(1, 80):
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
            try:
                name_el = card.query_selector('.name')
                if not name_el: continue
                cn = name_el.inner_text().strip()
            except: continue

            if cn not in name_to_id: continue

            new_pg = [None]
            def on_page(p): new_pg[0] = p
            ctx.on('page', on_page)
            card.evaluate('el => el.dispatchEvent(new MouseEvent("click", {bubbles:true}))')
            time.sleep(3)
            ctx.remove_listener('page', on_page)

            if new_pg[0] and 'spu?id=' in new_pg[0].url:
                try:
                    client.table('products').update({'product_url': new_pg[0].url})\
                        .eq('id', name_to_id[cn]).execute()
                    pf += 1; fixed += 1
                    del name_to_id[cn]
                except: pass
                new_pg[0].close()

            if not name_to_id: break

        print(f'  P{pn}: {pf} fixed, {len(name_to_id)} remain', flush=True)
        if not name_to_id: break
        if pf == 0 and pn >= 3: break  # 3 empty pages = done

    if not name_to_id: break

print(f'\nDone: {fixed} total', flush=True)
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
    .like('product_url','%#product=%').execute()
spu = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID)\
    .like('product_url','%/spu%').execute()
print(f'SPU:{spu.count} Fake:{fake.count}', flush=True)
ctx.close(); pw.stop()
