const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// Supabase/PostgREST caps a single request at 1000 rows, so we paginate.
const PAGE = 1000;
// Safety ceiling so a runaway query can't hang the serverless function forever.
const MAX_ROWS = 100000;

// Turn an Aliyun OSS thumbnail URL (`?x-oss-process=image/resize,...`) back into
// the original, directly-downloadable file. Leaves other URLs untouched.
function originalImageUrl(url) {
  if (!url) return '';
  try {
    const u = new URL(url);
    if (u.searchParams.has('x-oss-process')) {
      u.searchParams.delete('x-oss-process');
      if (u.searchParams.has('redesign_num')) u.searchParams.delete('redesign_num');
      return u.toString();
    }
    return url;
  } catch {
    return url.includes('x-oss-process') ? url.split('?')[0] : url;
  }
}

// `original_data` is stored as a JSON string; some scrapers put the supplier SKU
// (`code`) in there. Fall back to the DB id so every row still has an identifier.
function parseOriginalData(p) {
  const raw = p.original_data;
  if (!raw) return {};
  if (typeof raw === 'object') return raw;
  try { return JSON.parse(raw) || {}; } catch { return {}; }
}

function skuOf(p) {
  const od = parseOriginalData(p);
  if (od.code || od.sku) return String(od.code || od.sku);
  return String(p.id);
}

// Apply the same filter set as /api/search so export respects active filters.
function applyFilters(q, params) {
  if (params.q) q = q.or(`name.ilike.%${params.q}%,description.ilike.%${params.q}%`);
  if (params.category) q = q.eq('category', params.category);
  if (params.supplier_id) q = q.eq('supplier_id', parseInt(params.supplier_id));
  if (params.shipping_country) q = q.eq('shipping_country', params.shipping_country);
  if (params.product_type) q = q.eq('product_type', params.product_type);
  if (params.min_price) q = q.gte('price', parseFloat(params.min_price));
  if (params.max_price) q = q.lte('price', parseFloat(params.max_price));
  if (params.is_hot === 'true') q = q.eq('is_hot', true);
  if (params.is_new === 'true') q = q.eq('is_new', true);
  return q;
}

function enrich(p, supplierMap) {
  const s = supplierMap[p.supplier_id] || {};
  const od = parseOriginalData(p);

  // Colors may be strings or {color, origin_color} objects depending on scraper.
  const colors = Array.isArray(od.colors)
    ? od.colors.map(c => (typeof c === 'string' ? c : (c.color || c.origin_color || ''))).filter(Boolean)
    : (od.color ? [od.color] : []);
  const processes = Array.isArray(od.process)
    ? od.process
    : (Array.isArray(od.techniques) ? od.techniques : (od.technique ? [od.technique] : []));

  // Gallery: main image first, then any extra images captured by the scraper.
  const gallery = [];
  if (p.image_url) gallery.push(originalImageUrl(p.image_url));
  for (const u of (Array.isArray(od.images) ? od.images : [])) {
    const clean = originalImageUrl(u);
    if (clean && !gallery.includes(clean)) gallery.push(clean);
  }

  const delivery = p.delivery_days != null
    ? p.delivery_days
    : (od.production_cycle || od.human_production_cycle || '');

  return {
    factory_name: s.name || '',
    country: p.shipping_country || '',   // 发货国家（数据库唯一的国家字段）
    province: s.shipping_from || '',     // 工厂所在地（省份）
    sku: skuOf(p),
    category: p.category || '',
    name: p.name || '',
    image_links: gallery.join('\n'),    // 多图换行分隔，逐条保留原始可下载链接
    images: gallery,                    // JSON 下输出结构化数组
    material: (p.material_tags || []).join(';'),
    size: od.size || od.piece_size || '',
    color: colors.join(';'),
    process: processes.join(';'),
    price: p.price,
    currency: p.currency || '',
    stock: od.stock || od.stock_status || '',
    delivery_days: delivery,
    updated_at: p.last_seen_at || '',
    product_url: p.product_url || '',
  };
}

// [中文表头, 字段 key] — 顺序即导出列顺序。
const COLUMNS = [
  ['工厂名称', 'factory_name'],
  ['生产国家', 'country'],
  ['工厂所在地', 'province'],
  ['产品ID/SKU', 'sku'],
  ['品类', 'category'],
  ['产品名称', 'name'],
  ['主图原始链接', 'image_links'],
  ['材质', 'material'],
  ['尺寸/容量', 'size'],
  ['颜色', 'color'],
  ['支持工艺及定制范围', 'process'],
  ['价格', 'price'],
  ['币种', 'currency'],
  ['半成品库存/供货状态', 'stock'],
  ['生产时效(天)', 'delivery_days'],
  ['更新时间', 'updated_at'],
  ['产品链接', 'product_url'],
];

function csvCell(v) {
  const s = v === null || v === undefined ? '' : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv(products) {
  const headers = COLUMNS.map(c => c[0]);
  const keys = COLUMNS.map(c => c[1]);
  const lines = [headers.join(',')];
  for (const p of products) {
    lines.push(keys.map(k => csvCell(p[k])).join(','));
  }
  return lines.join('\n');
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { format = 'csv', ...params } = req.query;

  try {
    // 1. Exact count of matching rows (respects filters).
    const countQuery = applyFilters(
      supabase.from('products').select('id', { count: 'exact', head: true }).eq('is_active', true),
      params
    );
    const { count, error: countErr } = await countQuery;
    if (countErr) throw countErr;

    const total = Math.min(count || 0, MAX_ROWS);
    const pages = Math.ceil(total / PAGE);

    // 2. Fetch every page (plus suppliers) in parallel — much faster than a
    //    sequential loop and stays under the serverless timeout.
    const pageQueries = [];
    for (let i = 0; i < pages; i++) {
      pageQueries.push(
        applyFilters(
          supabase.from('products').select('*').eq('is_active', true),
          params
        ).order('id', { ascending: true }).range(i * PAGE, i * PAGE + PAGE - 1)
      );
    }

    const [suppliersRes, ...pageRes] = await Promise.all([
      supabase.from('suppliers').select('id, name, shipping_from'),
      ...pageQueries,
    ]);

    const supplierMap = {};
    for (const s of suppliersRes.data || []) supplierMap[s.id] = s;

    const products = [];
    for (const pr of pageRes) {
      if (pr.error) throw pr.error;
      products.push(...(pr.data || []));
    }

    const enriched = products.map(p => enrich(p, supplierMap));

    if (format === 'json') {
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Content-Disposition', 'attachment; filename="products.json"');
      return res.send(JSON.stringify({ total: enriched.length, products: enriched }, null, 2));
    }

    // CSV with BOM so Excel opens Chinese headers correctly.
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="products.csv"');
    return res.send('﻿' + toCsv(enriched));
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
