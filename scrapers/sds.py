"""Scraper for SDS (sdsdiy.com) — paginate __ALL__ for each shipping tab. Fast & resilient."""
import sys, os, re, time
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from common import insert_product, log_scrape

BASE_URL = 'https://www.sdsdiy.com'
SUPPLIER_ID = 6


def scrape():
    pw = sync_playwright().start()
    seen_names = set()
    new_count = 0

    def block(r):
        if r.request.resource_type in {'font', 'media'}: r.abort()
        else: r.continue_()

    def fresh_browser():
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu'])
        page = browser.new_page(viewport={'width': 1920, 'height': 1080}, locale='zh-CN')
        page.route('**/*', block)
        return browser, page

    browser, page = fresh_browser()
    url = f'{BASE_URL}/portal/search'
    print(f'Loading {url}...')
    try: page.goto(url, wait_until='networkidle', timeout=60000)
    except: pass
    time.sleep(4)

    # Get shipping tabs
    tab_els = page.query_selector_all('.tab__style-3Wf6jT')
    shipping_tabs = [el.inner_text().strip() for el in tab_els if el.inner_text().strip()]
    print(f'Shipping tabs: {shipping_tabs}')

    if not shipping_tabs:
        shipping_tabs = ['__DEFAULT__']

    for tab_idx, tab_name in enumerate(shipping_tabs):
        print(f'\n[Tab {tab_idx+1}/{len(shipping_tabs)}] {tab_name}', flush=True)

        if tab_name != '__DEFAULT__':
            for el in page.query_selector_all('.tab__style-3Wf6jT'):
                if el.inner_text().strip() == tab_name:
                    el.click(); time.sleep(3); break

        # Just paginate __ALL__ — no sub-category clicking
        pn = 1
        stale = 0
        tab_new = 0
        while pn <= 100:
            time.sleep(1)
            try: html = page.content()
            except: break
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('.newProductItem__style-WjoDb6')
            if not cards: break

            page_new = 0
            batch = []
            for card in cards:
                ne = card.select_one('.name__style-13O2qz')
                if not ne: continue
                name = ne.get_text(strip=True)
                if name in seen_names: continue
                seen_names.add(name); page_new += 1

                price = None
                pe = card.select_one('.price__style-3Fr3UH')
                if pe:
                    nums = re.findall(r'[\d.]+', pe.get_text(strip=True))
                    if nums:
                        try: price = float(nums[0])
                        except: pass

                img = None
                ie = card.select_one('.image__style-dg2gq5')
                if ie:
                    m = re.search(r'url\("([^"]+)"\)', ie.get('style',''))
                    if m: img = m.group(1)

                mats = []; dd = None
                for item in card.select('.infoItem__style-2yFutw'):
                    t = item.get_text(strip=True)
                    if '材质' in t:
                        mt = t.split('：',1)[-1].strip() if '：' in t else t.split(':',1)[-1].strip() if ':' in t else t
                        mats = [m.strip() for m in re.split(r'[+,,，、\s]+', mt) if m.strip()]
                    if '发货' in t or '时效' in t:
                        ns = re.findall(r'(\d+)', t)
                        if ns: dd = int(ns[0])

                batch.append({
                    'name': name, 'price': price, 'currency': 'CNY',
                    'delivery_days': dd, 'listed_at': None, 'is_hot': False,
                    'category': tab_name, 'material_tags': mats, 'image_url': img,
                    'product_url': f'{BASE_URL}/portal/search#product={quote(name, safe="")}',
                    'raw': {'supplier': 'SDS', 'shipping_tab': tab_name},
                })

            # Insert batch to DB
            for p in batch:
                if insert_product(SUPPLIER_ID, p): new_count += 1

            tab_new += page_new
            print(f'  P{pn}: {page_new}N/{len(cards)}C | total={len(seen_names)}', flush=True)

            if page_new == 0:
                stale += 1
                if stale >= 2: break
            else: stale = 0

            # Next page
            ok = False
            for s in ['.ant-pagination-next:not(.ant-pagination-disabled)',
                       'li[title="Next Page"]:not(.ant-pagination-disabled)']:
                try:
                    b = page.query_selector(s)
                    if b: b.click(); pn += 1; ok = True; break
                except: pass
            if not ok: break

        print(f'  Tab done: {tab_new} new this tab, {len(seen_names)} total unique', flush=True)

        # Restart browser between tabs
        if tab_idx < len(shipping_tabs) - 1:
            browser.close()
            print('  (restarting browser...)', flush=True)
            browser, page = fresh_browser()
            try: page.goto(url, wait_until='networkidle', timeout=60000)
            except: pass
            time.sleep(4)
            # Click next tab
            next_tab = shipping_tabs[tab_idx + 1]
            for el in page.query_selector_all('.tab__style-3Wf6jT'):
                if el.inner_text().strip() == next_tab:
                    el.click(); time.sleep(3); break

    log_scrape(SUPPLIER_ID, len(seen_names), new_count, 'success')
    print(f'\nDone! {len(seen_names)} unique, {new_count} new to DB')
    browser.close(); pw.stop()


if __name__ == '__main__':
    scrape()
