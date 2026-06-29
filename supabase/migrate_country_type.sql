-- Add columns for country and product type to supplier-dashboard
ALTER TABLE products ADD COLUMN IF NOT EXISTS shipping_country TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS product_type TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_products_shipping_country ON products (shipping_country);
CREATE INDEX IF NOT EXISTS idx_products_product_type ON products (product_type);
