-- Supplier Product Dashboard — Database Schema
-- Run this in Supabase SQL Editor

-- Extension for Chinese-compatible text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Suppliers table
CREATE TABLE IF NOT EXISTS suppliers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    website     TEXT NOT NULL,
    shipping_from TEXT,
    status      TEXT DEFAULT 'active',
    CONSTRAINT chk_supplier_status CHECK (status IN ('active', 'paused'))
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id            SERIAL PRIMARY KEY,
    supplier_id   INT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    description   TEXT,
    price         DECIMAL(10,2),
    price_unit    TEXT,
    currency      TEXT DEFAULT 'CNY',
    delivery_days INT,
    listed_at     DATE,
    is_hot        BOOLEAN DEFAULT FALSE,
    category      TEXT,
    material_tags TEXT[],
    image_url     TEXT,
    product_url   TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ DEFAULT NOW(),
    is_active     BOOLEAN DEFAULT TRUE,
    is_new        BOOLEAN DEFAULT FALSE,
    original_data JSONB,
    UNIQUE(supplier_id, product_url),
    CONSTRAINT chk_currency CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT chk_delivery_days CHECK (delivery_days IS NULL OR delivery_days > 0)
);

-- Scrape logs table
CREATE TABLE IF NOT EXISTS scrape_logs (
    id             SERIAL PRIMARY KEY,
    supplier_id    INT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    started_at     TIMESTAMPTZ DEFAULT NOW(),
    finished_at    TIMESTAMPTZ,
    products_found INT DEFAULT 0,
    products_new   INT DEFAULT 0,
    status         TEXT DEFAULT 'pending',
    CONSTRAINT chk_scrape_log_status CHECK (status IN ('pending', 'running', 'success', 'failed'))
);

-- Indexes for search performance
-- Trigram index for Chinese + English substring search
CREATE INDEX IF NOT EXISTS idx_products_name_trgm
    ON products USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_listed_at ON products (listed_at DESC);
CREATE INDEX IF NOT EXISTS idx_products_is_hot ON products (is_hot) WHERE is_hot = TRUE;
CREATE INDEX IF NOT EXISTS idx_products_is_new ON products (is_new) WHERE is_new = TRUE;
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products (is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_scrape_logs_supplier ON scrape_logs (supplier_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_status ON scrape_logs (status);

-- Seed: 5 MVP suppliers (UNIQUE(name) makes ON CONFLICT idempotent)
INSERT INTO suppliers (name, website, shipping_from) VALUES
    ('博亚达', 'http://www.xyldiy.com/', '福建'),
    ('海天城', 'http://www.htccustom.com/', '福建'),
    ('艺之冠', 'http://ykartwood.com/', '福建'),
    ('蔚来视野', 'https://www.wlsypod.com/', '广东'),
    ('指纹科技', 'https://www.hicustom.com/', '福建')
ON CONFLICT (name) DO NOTHING;
