"""Fix 指纹科技 URLs+images using logged-in SPU API calls."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
CHROME_PROFILE = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data\Default'
client = get_client()

prods = client.table('products').select('id,name').eq('supplier_id', SUPPLIER_ID).limit(5000).execute()
print(f'Total products: {len(prods.data)}', flush=True)

pw = sync_playwright().start()
ctx = pw.chromium.launch_persistent_context(
    user_data_dir=CHROME_PROFILE, headless=True,
    args=['--no-sandbox','--disable-gpu'],
    viewport={'width':1920,'height':1080}, locale='zh-CN'
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
          wait_until='domcontentloaded', timeout=30000)
time.sleep(3)
print('Session ready!', flush=True)

fixed_url = 0
fixed_img = 0
for i, p in enumerate(prods.data):
    full_name = p['name'].replace("'", "")
    result = None

    # Try multiple search strategies
    import re as _re
    parts = _re.split(r'[-（(）)\s]+', full_name)
    parts = [x for x in parts if len(x) >= 2]

    searches = [full_name[:15]]  # first 15 chars
    if parts:
        searches.append(parts[0])  # first word
    if len(parts) >= 2:
        searches.append(' '.join(parts[:2]))  # first two words
    searches.append(full_name[:25])  # longer

    # Deduplicate
    seen = set()
    searches = [s for s in searches if not (s in seen or seen.add(s))]

    for search in searches:
        if len(search) < 2: continue
        try:
            r = page.evaluate(f'''async () => {{
                const resp = await fetch('https://apigw.hihumbird.com/spu-itg/uct/v1/spus/page', {{
                    method: 'POST', headers: {{'Content-Type':'application/json'}},
                    body: JSON.stringify({{app_id:'2483999', name:'{search}', is_filter_reference:1, size:2, current:1}})
                }});
                const d = await resp.json();
                const list = d.data?.list || [];
                if (list.length > 0) {{
                    const item = list[0];
                    return {{id: item.id, img: item.image?.file_path || ''}};
                }}
                return null;
            }}''')
        except: continue
        if r and r.get('id'):
            result = r
            break

    if result and result.get('id'):
        spu_url = f'https://jit.hicustom.com/spu?id={result["id"]}'
        update = {'product_url': spu_url}
        if result.get('img'):
            update['image_url'] = f'https://nimg5.hicustom.com/{result["img"]}'
        try:
            client.table('products').update(update).eq('id', p['id']).execute()
            fixed_url += 1
            if result.get('img'): fixed_img += 1
        except: pass

    if (i+1) % 200 == 0:
        print(f'  {i+1}/{len(prods.data)}: {fixed_url} URLs, {fixed_img} imgs', flush=True)

print(f'\nDone: {fixed_url} URLs, {fixed_img} images', flush=True)

total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).like('product_url','%#product=%').execute()
bad = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).or_('image_url.is.null,image_url.ilike.%image-error%').execute()
print(f'Real URLs: {total.count-fake.count}/{total.count}, Bad img: {bad.count}', flush=True)
ctx.close(); pw.stop()
