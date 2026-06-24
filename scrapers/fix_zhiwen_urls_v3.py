"""Fix 指纹科技 URLs — SPU API keyword search per product name."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
client = get_client()

# Get products with fake URLs
prods = client.table('products').select('id,name,product_url').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').limit(5000).execute()
print(f'Fake URLs: {len(prods.data)}', flush=True)

if not prods.data:
    print('All done!')
    exit()

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

# Load page for auth
try: page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
               wait_until='networkidle', timeout=30000)
except: pass
time.sleep(3)

fixed = 0
for i, p in enumerate(prods.data):
    name = p['name']
    # Search SPU API by name
    try:
        result = page.evaluate(f'''async () => {{
            const resp = await fetch('https://apigw.hihumbird.com/spu-itg/uct/v1/spus/page', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    app_id: '2483999', name: '{name[:80].replace(chr(39), "")}',
                    sort_center_app_country_codes: ['US','CN'],
                    is_filter_reference: 1, size: 3, current: 1
                }})
            }});
            const d = await resp.json();
            const list = d.data?.list || [];
            if (list.length > 0) {{
                const item = list[0];
                const img = item.image?.file_path || item.image || '';
                return {{id: item.id, img: img}};
            }}
            return null;
        }}''')
    except:
        continue

    if result:
        spu_id = result.get('id')
        img_path = result.get('img', '')
        if spu_id:
            spu_url = f'https://jit.hicustom.com/spu?id={spu_id}'
            update_data = {'product_url': spu_url}
            if img_path:
                update_data['image_url'] = f'https://nimg5.hicustom.com/{img_path}'
            try:
                client.table('products').update(update_data).eq('id', p['id']).execute()
                fixed += 1
            except: pass

    if (i + 1) % 100 == 0:
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed', flush=True)
        time.sleep(1)  # Rate limit pause

print(f'\nDone: {fixed} URLs updated', flush=True)

# Check result
total = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).execute()
fake = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID)\
    .like('product_url', '%#product=%').execute()
print(f'指纹科技: {total.count-fake.count}/{total.count} real URLs', flush=True)

browser.close(); pw.stop()
