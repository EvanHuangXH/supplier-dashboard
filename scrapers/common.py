"""Shared utilities for supplier scrapers."""
import os
import sys
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Browser, Page
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_client: Optional[Client] = None
_browser: Optional[Browser] = None
_playwright = None


def get_client() -> Client:
    """Get or create Supabase client (singleton)."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def get_supplier_id(name: str) -> int:
    """Resolve supplier name to DB id."""
    client = get_client()
    result = client.table("suppliers").select("id").eq("name", name).single().execute()
    return result.data["id"]


def _get_browser() -> Browser:
    """Get or create Playwright browser (singleton, reused across pages)."""
    global _browser, _playwright
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
    return _browser


def fetch_html(url: str, max_retries: int = 3, wait_for: str = "networkidle") -> str:
    """Fetch a fully rendered page using headless Chromium.

    Args:
        url: Page URL to fetch
        max_retries: Number of retry attempts
        wait_for: Playwright wait strategy - 'networkidle' for SPAs,
                  'domcontentloaded' for static pages

    Returns:
        Rendered HTML string
    """
    browser = _get_browser()
    last_error = None

    for attempt in range(1, max_retries + 1):
        page: Optional[Page] = None
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            # Block unnecessary resources for speed
            def block_unnecessary(route):
                if route.request.resource_type in {"image", "font", "media"}:
                    route.abort()
                else:
                    route.continue_()
            page.route("**/*", block_unnecessary)
            page.goto(url, wait_until=wait_for, timeout=30000)
            # Extra wait for dynamic content
            page.wait_for_timeout(2000)
            html = page.content()
            page.close()
            return html
        except Exception as e:
            last_error = e
            print(f"  [Attempt {attempt}/{max_retries}] {url} failed: {e}")
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if attempt < max_retries:
                time.sleep(3 * attempt)

    raise last_error


def cleanup_browser():
    """Close browser and stop Playwright. Call at end of script."""
    global _browser, _playwright
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright:
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = None


def insert_product(supplier_id: int, data: Dict[str, Any]) -> bool:
    """Insert a product. Returns True if new, False if duplicate skipped."""
    client = get_client()

    # Default listed_at to today if not provided by scraper
    listed_at = data.get("listed_at")
    if listed_at is None:
        listed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    product_data = {
        "supplier_id": supplier_id,
        "name": data.get("name", ""),
        "description": data.get("description"),
        "price": data.get("price"),
        "price_unit": data.get("price_unit"),
        "currency": data.get("currency", "CNY"),
        "delivery_days": data.get("delivery_days"),
        "listed_at": listed_at,
        "is_hot": data.get("is_hot", False),
        "category": data.get("category"),
        "material_tags": data.get("material_tags", []),
        "image_url": data.get("image_url"),
        "product_url": data["product_url"],
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "is_new": True,
        "original_data": json.dumps(data.get("raw", {}), ensure_ascii=False),
    }

    existing = (
        client.table("products")
        .select("id, image_url, product_url, category")
        .eq("supplier_id", supplier_id)
        .eq("product_url", data["product_url"])
        .execute()
    )

    if existing.data:
        existing_rec = existing.data[0]
        update_data = {
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
        # Update image_url if existing product has no image or error placeholder
        new_img = data.get("image_url")
        if new_img and "image-error" not in (new_img or ""):
            existing_img = existing_rec.get("image_url", "")
            if not existing_img or "image-error" in (existing_img or ""):
                update_data["image_url"] = new_img
        # Upgrade hash-based URL to real detail URL
        new_url = data.get("product_url", "")
        old_url = existing_rec.get("product_url", "")
        if new_url and "#product=" not in new_url and "#product=" in (old_url or ""):
            update_data["product_url"] = new_url
        # Fill in category if existing record has none
        new_cat = data.get("category")
        if new_cat:
            old_cat = existing_rec.get("category")
            if not old_cat:
                update_data["category"] = new_cat
        if len(update_data) > 2:  # More than just last_seen_at + is_active
            client.table("products").update(update_data).eq("id", existing_rec["id"]).execute()
        return False

    client.table("products").insert(product_data).execute()
    return True


def log_scrape(supplier_id: int, found: int, new: int, status: str):
    """Record a scrape run in scrape_logs."""
    client = get_client()
    client.table("scrape_logs").insert({
        "supplier_id": supplier_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "products_found": found,
        "products_new": new,
        "status": status,
    }).execute()


def reset_new_flag(supplier_id: int):
    """Clear is_new for products older than today."""
    client = get_client()
    client.table("products").update({"is_new": False}).eq(
        "supplier_id", supplier_id
    ).eq("is_new", True).execute()


def run_scraper(supplier_name: str, scrape_fn):
    """Wrapper: resolve supplier, run scraper, log results, cleanup."""
    print(f"\n{'='*60}")
    print(f"Starting: {supplier_name}")
    print(f"{'='*60}")

    try:
        supplier_id = get_supplier_id(supplier_name)
        print(f"  Supplier ID: {supplier_id}")

        products = scrape_fn()
        found = len(products)
        new_count = 0

        for product in products:
            is_new = insert_product(supplier_id, product)
            if is_new:
                new_count += 1
                print(f"  NEW: {product.get('name', 'Unknown')}")
            else:
                print(f"  SKIP: {product.get('name', 'Unknown')} (exists)")

        log_scrape(supplier_id, found, new_count, "success")
        print(f"\n  Done: {found} found, {new_count} new")

    except Exception as e:
        print(f"\n  FAILED: {e}")
        try:
            supplier_id = get_supplier_id(supplier_name)
            log_scrape(supplier_id, 0, 0, "failed")
        except Exception:
            pass
        sys.exit(1)
    finally:
        cleanup_browser()
