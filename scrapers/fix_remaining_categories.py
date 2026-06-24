"""Fix remaining categories with full pagination — 海天城, 极特 (sdspod) + JVCustom."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from common import get_client

# === sdspod sites: paginate through each warehouse ===
SDSPOD = [
    ('海天城', 'http://www.htccustom.com', 2, '.productItem__style-JSa88h', '.name__style-LDYYfw'),
    ('极特', 'http://www.podjit.com', 11, '.productItem__style-JSa88h', '.name__style-LDYYfw'),
]

client = get_client()

for supplier_name, base_url, sid, card_sel, name_sel in SDSPOD:
    total = client.table('products').select('id',count='exact').eq('supplier_id',sid).execute()
    with_cat = client.table('products').select('id',count='exact').eq('supplier_id',sid).not_.is_('category','null').execute()
    need = total.count - with_cat.count
    if need == 0:
        print(f'{supplier_name}: all done! ({with_cat.count}/{total.count})')
        continue
    print(f'{supplier_name}: {need} need ({with_cat.count}/{total.count})', flush=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    def block(r):
        if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    try: page.goto(f'{base_url}/portal/search', wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(3)

    # Get warehouse tabs
    warehouses = []
    tab_els = page.query_selector_all('.tab__style-3Wf6jT')
    if not tab_els:
        # Try sdspod warehouse sidebar
        tab_els = page.query_selector_all('[class*=rootItem]')
    for el in tab_els:
        try:
            text = el.inner_text().strip()
            if text and text not in warehouses:
                warehouses.append(text)
        except: pass

    if not warehouses:
        print('  No warehouses found, trying page-based approach')
        warehouses = ['__ALL__']

    fixed = 0
    for wh_name in warehouses:
        if wh_name != '__ALL__':
            for el in page.query_selector_all('.tab__style-3Wf6jT, [class*=rootItem]'):
                try:
                    if el.inner_text().strip() == wh_name:
                        el.click(); time.sleep(2); break
                except: pass

        # Paginate through all pages in this warehouse
        pn = 1
        stale = 0
        while pn <= 30:
            time.sleep(1)
            cards = page.query_selector_all(card_sel)
            if not cards: break

            wh_fixed = 0
            for card in cards:
                try:
                    name_el = card.query_selector(name_sel)
                    if not name_el: continue
                    name = name_el.inner_text().strip()
                    if not name: continue
                    client.table('products').update({'category': wh_name if wh_name != '__ALL__' else None})\
                        .eq('supplier_id', sid).eq('name', name).execute()
                    wh_fixed += 1
                except: pass

            fixed += wh_fixed

            # Next page
            clicked = False
            for s in ['.ant-pagination-next:not(.ant-pagination-disabled)',
                       'li[title="Next Page"]:not(.ant-pagination-disabled)']:
                try:
                    btn = page.query_selector(s)
                    if btn: btn.click(); pn += 1; clicked = True; time.sleep(1.5); break
                except: pass
            if not clicked: break

        if wh_fixed == 0: print(f'  {wh_name[:40]}: paged', end=' ', flush=True)

    with_cat2 = client.table('products').select('id',count='exact').eq('supplier_id',sid).not_.is_('category','null').execute()
    print(f'\n  Done: {with_cat2.count}/{total.count} ({round(with_cat2.count/total.count*100,1)}%)', flush=True)
    browser.close(); pw.stop()

# === JVCustom: paginate through factory categories ===
print()
sid = 7
total = client.table('products').select('id',count='exact').eq('supplier_id',sid).execute()
with_cat = client.table('products').select('id',count='exact').eq('supplier_id',sid).not_.is_('category','null').execute()
need = total.count - with_cat.count
if need == 0:
    print(f'JVCustom: all done!')
else:
    print(f'JVCustom: {need} need ({with_cat.count}/{total.count})', flush=True)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
    def block(r):
        if r.request.resource_type in {'font', 'media', 'image'}: r.abort()
        else: r.continue_()
    page.route('**/*', block)

    try: page.goto('https://www.jvcustom.com/custom', wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(4)

    # Get factory/location categories
    factory_kw = ['工厂', '直发', '美国', '英国', '德国', '法国', '日本', '韩国', '加拿大', '澳大利亚',
                  '墨西哥', '巴西', '意大利', '西班牙', '荷兰', '生产', '服饰', '家居', '全品类',
                  '福建', '广东', '浙江', '中国', '莆田', '深圳', '广州', '纽约', '加州', '皇后']
    filter_kw = ['元', 'g', '天', '低到高', '高到低', '上架时间', '默认', '重量', '价格']

    cat_els = page.query_selector_all('[class*=categ] a, [class*=categ] li, .filter-item, #category_filter option')
    categories = []
    for el in cat_els:
        try:
            text = el.inner_text().strip()
            if text and text not in categories and len(text) < 60:
                if any(kw in text for kw in factory_kw) and not any(kw in text for kw in filter_kw):
                    categories.append(text)
        except: pass
    print(f'  Factory categories: {len(categories)}', flush=True)

    fixed = 0
    for ci, cat_name in enumerate(categories):
        # Click category
        for el in page.query_selector_all('[class*=categ] a, [class*=categ] li, .filter-item'):
            try:
                if el.inner_text().strip() == cat_name:
                    el.click(); time.sleep(2); break
            except: pass

        # Paginate
        pn = 1
        while pn <= 10:
            time.sleep(1)
            cards = page.query_selector_all('.card-product')
            if not cards: break

            cat_fixed = 0
            for card in cards:
                try:
                    name_el = card.query_selector('h3.card-title a') or card.query_selector('.card-body h3 a')
                    if not name_el: continue
                    name = name_el.inner_text().strip()
                    if not name: continue
                    client.table('products').update({'category': cat_name})\
                        .eq('supplier_id', sid).eq('name', name).execute()
                    cat_fixed += 1
                except: pass
            fixed += cat_fixed

            # Next
            clicked = False
            for s in ['.ant-pagination-next:not(.ant-pagination-disabled)',
                       'li[title="Next Page"]:not(.ant-pagination-disabled)']:
                try:
                    btn = page.query_selector(s)
                    if btn: btn.click(); pn += 1; clicked = True; break
                except: pass
            if not clicked: break

        if ci % 5 == 0:
            print(f'  [{ci+1}/{len(categories)}] {cat_name[:30]}: updated', flush=True)

    with_cat2 = client.table('products').select('id',count='exact').eq('supplier_id',sid).not_.is_('category','null').execute()
    print(f'  Done: {with_cat2.count}/{total.count} ({round(with_cat2.count/total.count*100,1)}%)', flush=True)
    browser.close(); pw.stop()

print('\nAll done!')
