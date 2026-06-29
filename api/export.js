const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { format = 'csv', ...filters } = req.query;

  // Same filtering logic as search.js
  let query = supabase
    .from('products')
    .select('*, suppliers!inner(name, website, shipping_from)')
    .eq('is_active', true);

  if (filters.q) query = query.or(`name.ilike.%${filters.q}%,description.ilike.%${filters.q}%`);
  if (filters.category) query = query.eq('category', filters.category);
  if (filters.supplier_id) query = query.eq('supplier_id', parseInt(filters.supplier_id));
  if (filters.shipping_country) query = query.eq('shipping_country', filters.shipping_country);
  if (filters.product_type) query = query.eq('product_type', filters.product_type);
  if (filters.min_price) query = query.gte('price', parseFloat(filters.min_price));
  if (filters.max_price) query = query.lte('price', parseFloat(filters.max_price));
  if (filters.date_from) query = query.gte('listed_at', filters.date_from);
  if (filters.date_to) query = query.lte('listed_at', filters.date_to);

  query = query.order('listed_at', { ascending: false }).limit(10000);

  const { data, error } = await query;

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  if (format === 'json') {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', 'attachment; filename="products.json"');
    return res.json(data);
  }

  // CSV export
  const headers = [
    '产品名', '价格', '单位', '币种', '交期(天)', '上线日期',
    '热门', '国家', '产品类型', '分类', '材质', '图片链接', '产品链接',
    '供应商', '发货地', '首次发现', '最后更新'
  ];
  const rows = data.map(p => [
    p.name, p.price, p.price_unit, p.currency, p.delivery_days,
    p.listed_at, p.is_hot ? '是' : '否', p.shipping_country || '', p.product_type || '',
    p.category, (p.material_tags || []).join(';'), p.image_url, p.product_url,
    p.suppliers?.name, p.suppliers?.shipping_from,
    p.first_seen_at, p.last_seen_at
  ]);

  const csv = [
    headers.join(','),
    ...rows.map(r => r.map(c => `"${(c || '').toString().replace(/"/g, '""')}"`).join(','))
  ].join('\n');

  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="products.csv"');
  // Add BOM for Excel UTF-8 compatibility
  return res.send('﻿' + csv);
};
