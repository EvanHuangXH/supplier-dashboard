"""指纹科技: 通过 SPU API 补全产品详情链接和图片 (multi-pass fuzzy matching)."""
import sys, os, time, json, re, unicodedata
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

client = get_client()
sid = 5


def normalize_name(n):
    """Normalize product name for comparison."""
    # Remove parenthetical notes
    n = re.sub(r'[（(][^）)]*[）)]', '', n)
    # Normalize full-width to half-width
    n = unicodedata.normalize('NFKC', n)
    # Collapse whitespace
    n = re.sub(r'\s+', '', n)
    return n.lower()


# Get all 指纹科技 products
products = client.table('products').select('id,name,product_url,image_url')\
    .eq('supplier_id', sid).limit(5000).execute()
print(f'Total 指纹科技 products: {len(products.data)}', flush=True)

# Build lookup: name → record  (last-write-wins for duplicates)
db_by_name = {}
db_normalized = {}  # normalized name → record
for p in products.data:
    db_by_name[p['name']] = p
    db_normalized[normalize_name(p['name'])] = p
print(f'Unique names: {len(db_by_name)}, normalized: {len(db_normalized)}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')

# Load JIT page first to get cookies
print('Loading JIT page for auth cookies...', flush=True)
try:
    page.goto('https://www.hicustom.com/productType/allGoods?isSearch=1&tab=jit&page=1',
              wait_until='domcontentloaded', timeout=30000)
except: pass
try: page.wait_for_selector('.product-card', timeout=10000)
except: pass
time.sleep(2)

api_url = 'https://apigw.hihumbird.com/spu-itg/uct/v1/spus/page'
country_groups = [
    (['US','IT','ES','CA','MX','UK','AU','JP','BR','MY','DE','PH','PL','TH','ID'], 'JIT'),
    (['CN'], '国内'),
]

url_updated = 0
img_updated = 0
exact_matches = 0
normalized_matches = 0
fuzzy_matches = 0

for countries, label in country_groups:
    page_num = 1
    stale = 0
    print(f'\n[{label}] Starting...', flush=True)

    while True:
        payload = {
            'app_id': '2483999', 'delivery_period_filters': [], 'weight_filters': [],
            'sort_center_app_country_codes': countries,
            'is_filter_reference': 1, 'size': 100, 'current': page_num,
        }
        js = '''async (args) => {
            const resp = await fetch(args.url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(args.payload)
            });
            return await resp.json();
        }'''
        result = page.evaluate(js, {'url': api_url, 'payload': payload})
        spu_list = result.get('data', {}).get('list', [])
        total = result.get('data', {}).get('total', 0)

        if not spu_list:
            print(f'  [{label}] Page {page_num}: 0 records, done', flush=True)
            break

        matched = 0
        for spu in spu_list:
            api_name = spu.get('name', '')
            if not api_name: continue

            # Pass 1: Exact match
            db_rec = db_by_name.get(api_name)
            match_type = 'exact'
            if db_rec:
                exact_matches += 1
            else:
                # Pass 2: Normalized match
                norm_api = normalize_name(api_name)
                db_rec = db_normalized.get(norm_api)
                if db_rec:
                    match_type = 'normalized'
                    normalized_matches += 1

            if not db_rec:
                continue

            matched += 1
            spu_id = spu.get('id', '')
            product_url = f'https://jit.hicustom.com/spu?id={spu_id}' if spu_id else None

            img_info = spu.get('image', {})
            file_path = img_info.get('file_path', '')
            image_url = f'https://nimg5.hicustom.com/{file_path}' if file_path else None

            update_data = {}
            if product_url:
                update_data['product_url'] = product_url
            if image_url:
                update_data['image_url'] = image_url
            if update_data:
                try:
                    client.table('products').update(update_data).eq('id', db_rec['id']).execute()
                    url_updated += 1
                    if image_url: img_updated += 1
                except Exception:
                    pass

            # Remove from all lookups
            db_by_name.pop(db_rec['name'], None)
            db_normalized.pop(normalize_name(db_rec['name']), None)

        print(f'  [{label}] P{page_num}: {matched} matched ({match_type}), {len(db_by_name)} remain', flush=True)

        # Stop conditions
        if not db_by_name:
            print(f'  [{label}] All matched!', flush=True)
            break
        if matched == 0:
            stale += 1
            if stale >= 5:
                print(f'  [{label}] 5 stale pages, stopping', flush=True)
                break
        else:
            stale = 0
        if len(spu_list) < 100:
            break
        if page_num >= 200:
            print(f'  [{label}] 200 page limit', flush=True)
            break
        page_num += 1
        time.sleep(0.3)

# Pass 3: Fuzzy matching for remaining (requires rapidfuzz)
remaining = len(db_by_name)
if remaining > 0:
    print(f'\nPass 3: Fuzzy matching {remaining} remaining...', flush=True)
    try:
        from rapidfuzz import process, fuzz
        # Re-query API with first few pages of JIT data for fuzzy matching pool
        api_names = []
        for countries, label in country_groups:
            for pn in range(1, 6):  # Re-check first 5 pages
                payload = {
                    'app_id': '2483999', 'delivery_period_filters': [], 'weight_filters': [],
                    'sort_center_app_country_codes': countries,
                    'is_filter_reference': 1, 'size': 100, 'current': pn,
                }
                result = page.evaluate(js, {'url': api_url, 'payload': payload})
                spu_list = result.get('data', {}).get('list', [])
                for spu in spu_list:
                    name = spu.get('name', '')
                    if name: api_names.append((name, spu))
                if len(spu_list) < 100: break

        db_names = list(db_by_name.keys())
        for db_name in db_names[:]:
            result = process.extractOne(db_name, [a[0] for a in api_names],
                                        scorer=fuzz.ratio, score_cutoff=85)
            if result:
                matched_api_name = result[0]
                # Find the SPU data
                for api_name, spu in api_names:
                    if api_name == matched_api_name:
                        spu_id = spu.get('id', '')
                        product_url = f'https://jit.hicustom.com/spu?id={spu_id}' if spu_id else None
                        img_info = spu.get('image', {})
                        file_path = img_info.get('file_path', '')
                        image_url = f'https://nimg5.hicustom.com/{file_path}' if file_path else None
                        db_rec = db_by_name[db_name]
                        update_data = {}
                        if product_url: update_data['product_url'] = product_url
                        if image_url: update_data['image_url'] = image_url
                        if update_data:
                            try:
                                client.table('products').update(update_data).eq('id', db_rec['id']).execute()
                                url_updated += 1
                                if image_url: img_updated += 1
                                fuzzy_matches += 1
                            except: pass
                        del db_by_name[db_name]
                        break
        print(f'  Fuzzy: {fuzzy_matches} matched', flush=True)
    except ImportError:
        print('  rapidfuzz not installed, skipping fuzzy pass', flush=True)

print(f'\n{"="*50}')
print(f'Done: {url_updated} URLs updated, {img_updated} images updated')
print(f'  Exact: {exact_matches}, Normalized: {normalized_matches}, Fuzzy: {fuzzy_matches}')
print(f'  Remaining unmatched: {len(db_by_name)}')
print(f'{"="*50}')

page.close(); browser.close(); pw.stop()
