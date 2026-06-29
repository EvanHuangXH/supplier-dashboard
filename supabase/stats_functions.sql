-- Aggregation functions for stats API (bypasses Supabase 1000-row limit)

-- Country counts
CREATE OR REPLACE FUNCTION get_country_counts(supplier_id_param INT DEFAULT NULL)
RETURNS TABLE(name TEXT, count BIGINT) AS $$
BEGIN
  RETURN QUERY
  SELECT p.shipping_country, COUNT(*)::BIGINT
  FROM products p
  WHERE p.is_active = true AND p.shipping_country IS NOT NULL
    AND (supplier_id_param IS NULL OR p.supplier_id = supplier_id_param)
  GROUP BY p.shipping_country
  ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Product type counts
CREATE OR REPLACE FUNCTION get_type_counts(supplier_id_param INT DEFAULT NULL)
RETURNS TABLE(name TEXT, count BIGINT) AS $$
BEGIN
  RETURN QUERY
  SELECT p.product_type, COUNT(*)::BIGINT
  FROM products p
  WHERE p.is_active = true AND p.product_type IS NOT NULL
    AND (supplier_id_param IS NULL OR p.supplier_id = supplier_id_param)
  GROUP BY p.product_type
  ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Category counts
CREATE OR REPLACE FUNCTION get_category_counts(supplier_id_param INT DEFAULT NULL)
RETURNS TABLE(name TEXT, count BIGINT) AS $$
BEGIN
  RETURN QUERY
  SELECT p.category, COUNT(*)::BIGINT
  FROM products p
  WHERE p.is_active = true AND p.category IS NOT NULL
    AND (supplier_id_param IS NULL OR p.supplier_id = supplier_id_param)
  GROUP BY p.category
  ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;
