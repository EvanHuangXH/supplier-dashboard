"""Fix ALL 指纹科技 images using SPU API keyword search."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 5
client = get_client()

# Get ALL products (not just fake URLs)
prods = client.table('products').select('id,name,image_url').eq('supplier_id', SUPPLIER_ID).limit(5000).execute()
print(f'Total: {len(prods.data)} products', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

try: page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
               wait_until='networkidle', timeout=30000)
except: pass
time.sleep(3)

fixed = 0
for i, p in enumerate(prods.data):
    name = p['name']
    try:
        result = page.evaluate(f'''async () => {{
            const resp = await fetch('https://apigw.hihumbird.com/spu-itg/uct/v1/spus/page', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    app_id: '2483999', name: '{name[:80].replace(chr(39), "")}',
                    sort_center_app_country_codes: ['US','CN'],
                    is_filter_reference: 1, size: 2, current: 1
                }})
            }});
            const d = await resp.json();
            const list = d.data?.list || [];
            if (list.length > 0) {{
                const item = list[0];
                return {{id: item.id, img: item.image?.file_path || ''}};
            }}
            return null;
        }}''')
    except:
        continue

    if result and result.get('img'):
        img_url = f'https://nimg5.hicustom.com/{result["img"]}'
        spu_id = result.get('id')
        update_data = {'image_url': img_url}
        if spu_id:
            update_data['product_url'] = f'https://jit.hicustom.com/spu?id={spu_id}'
        try:
            client.table('products').update(update_data).eq('id', p['id']).execute()
            fixed += 1
        except: pass

    if (i + 1) % 200 == 0:
        print(f'  {i+1}/{len(prods.data)}: {fixed} fixed', flush=True)
        time.sleep(1)

print(f'\nDone: {fixed} images updated', flush=True)

# Check results
bad = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID)\
    .or_('image_url.is.null,image_url.ilike.%image-error%').execute()
no_img = client.table('products').select('id',count='exact').eq('supplier_id', SUPPLIER_ID).is_('image_url','null').execute()
print(f'Bad/Null images: {bad.count}')
browser.close(); pw.stop()
