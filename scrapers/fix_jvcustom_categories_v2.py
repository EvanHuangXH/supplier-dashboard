"""Fix JVCustom categories — only factory/location categories, skip price/weight filters."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

SUPPLIER_ID = 7
BASE_URL = 'https://www.jvcustom.com'

client = get_client()
total = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).execute()
with_cat = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).not_.is_('category','null').execute()
print(f'JVCustom before: {with_cat.count}/{total.count}', flush=True)

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
def block(r):
    if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
    else: r.continue_()
page.route('**/*', block)

try: page.goto(f'{BASE_URL}/custom', wait_until='networkidle', timeout=60000)
except: pass
time.sleep(4)

# Get category items
cat_els = page.query_selector_all('[class*=categ] a, [class*=categ] li, .filter-item, #category_filter option')
all_cats = []
for el in cat_els:
    try:
        text = el.inner_text().strip()
        if text and len(text) < 60 and text not in all_cats:
            all_cats.append(text)
    except: pass

# Filter: only keep factory/location categories
# Factory keywords: 工厂, 直发, 国家名, 地区名
factory_keywords = ['工厂', '直发', '美国', '英国', '德国', '法国', '日本', '韩国', '加拿大', '澳大利亚',
                    '墨西哥', '巴西', '意大利', '西班牙', '荷兰', '生产', '全品类', '服饰', '家居',
                    '福建', '广东', '浙江', '中国', '莆田', '深圳', '广州', '纽约', '加州', '皇后']
filter_keywords = ['元', 'g', '天', '低到高', '高到低', '新旧', '默认', '重量', '价格', '时间']

categories = []
for cat in all_cats:
    is_filter = any(kw in cat for kw in filter_keywords)
    is_factory = any(kw in cat for kw in factory_keywords)
    if is_factory and not is_filter:
        categories.append(cat)
    elif not is_filter and len(cat) <= 6:
        # Short names are likely factory codes/locations
        categories.append(cat)

categories = list(dict.fromkeys(categories))
print(f'Factory categories: {len(categories)} (from {len(all_cats)} total)', flush=True)
for c in categories[:15]:
    print(f'  {c}')

fixed = 0
for ci, cat_name in enumerate(categories):
    # Click category
    clicked = False
    for el in page.query_selector_all('[class*=categ] a, [class*=categ] li, .filter-item'):
        try:
            if el.inner_text().strip() == cat_name:
                el.click(); time.sleep(2); clicked = True; break
        except: pass
    if not clicked: continue

    # Update products on page
    cards = page.query_selector_all('.card-product')
    cat_fixed = 0
    for card in cards:
        try:
            name_el = card.query_selector('h3.card-title a') or card.query_selector('.card-body h3 a')
            if not name_el: continue
            name = name_el.inner_text().strip()
            if not name: continue
            client.table('products').update({'category': cat_name})\
                .eq('supplier_id', SUPPLIER_ID).eq('name', name).execute()
            cat_fixed += 1
        except: pass

    if cat_fixed > 0: fixed += cat_fixed
    if ci % 5 == 0:
        print(f'  [{ci+1}/{len(categories)}] {cat_name}: {cat_fixed} updated', flush=True)

with_cat2 = client.table('products').select('id',count='exact').eq('supplier_id',SUPPLIER_ID).not_.is_('category','null').execute()
print(f'JVCustom after: {with_cat2.count}/{total.count} ({round(with_cat2.count/total.count*100,1)}%)', flush=True)
browser.close(); pw.stop()
