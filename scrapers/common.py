"""Shared utilities for supplier scrapers."""
import os
import sys
import time
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_client: Optional[Client] = None


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


def fetch_page(url: str, max_retries: int = 3) -> str:
    """Fetch a page with retries and browser-like headers."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            last_error = e
            print(f"  [Attempt {attempt}/{max_retries}] {url} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
    raise last_error


def insert_product(supplier_id: int, data: Dict[str, Any]) -> bool:
    """Insert a product. Returns True if new, False if duplicate skipped."""
    client = get_client()

    product_data = {
        "supplier_id": supplier_id,
        "name": data.get("name", ""),
        "description": data.get("description"),
        "price": data.get("price"),
        "price_unit": data.get("price_unit"),
        "currency": data.get("currency", "CNY"),
        "delivery_days": data.get("delivery_days"),
        "listed_at": data.get("listed_at"),
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
        .select("id")
        .eq("supplier_id", supplier_id)
        .eq("product_url", data["product_url"])
        .execute()
    )

    if existing.data:
        # Update last_seen_at only, do not change other fields
        client.table("products").update({
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }).eq("id", existing.data[0]["id"]).execute()
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
    """Clear is_new for products older than today (called before each run)."""
    client = get_client()
    client.table("products").update({"is_new": False}).eq(
        "supplier_id", supplier_id
    ).eq("is_new", True).execute()


def run_scraper(supplier_name: str, scrape_fn):
    """Wrapper: resolve supplier, run scraper, log results."""
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
