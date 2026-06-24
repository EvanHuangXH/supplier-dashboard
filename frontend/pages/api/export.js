const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { format = 'csv', q, category, supplier_id, shipping_country, product_type, min_price, max_price, is_hot, is_new, ...rest } = req.query;

  let query = supabase
    .from('products')
    .select('*, suppliers!inner(name, website, shipping_from)')
    .eq('is_active', true);

  if (q) query = query.or(`name.ilike.%${q}%,description.ilike.%${q}%`);
  if (category) query = query.eq('category', category);
  if (supplier_id) query = query.eq('supplier_id', parseInt(supplier_id));
  if (shipping_country) query = query.like('category', `%${shipping_country}%`);
  if (product_type) query = query.like('category', `%TYPE:${product_type}%`);
  if (min_price) query = query.gte('price', parseFloat(min_price));
  if (max_price) query = query.lte('price', parseFloat(max_price));
  if (is_hot === 'true') query = query.eq('is_hot', true);
  if (is_new === 'true') {
    const today = new Date().toISOString().slice(0, 10);
    query = query.gte('first_seen_at', today);
  }

  query = query.order('first_seen_at', { ascending: false }).limit(10000);

  const { data, error } = await query;

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  if (format === 'json') {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', 'attachment; filename="products.json"');
    return res.json(data);
  }

  // Extract country and type from category field
  const extractCountry = (cat) => {
    const countries = ['美国','加拿大','墨西哥','英国','德国','法国','澳大利亚','日本','韩国','意大利','西班牙','荷兰','巴西','中国'];
    for (const c of countries) {
      if ((cat || '').includes(c)) return c;
    }
    return '';
  };
  const extractType = (cat) => {
    const m = (cat || '').match(/TYPE:(\S+)/);
    return m ? m[1] : '';
  };

  // CSV export with enhanced columns
  const headers = [
    '产品名', '价格(¥)', '币种', '国家', '产品类型',
    '分类', '交期(天)', '供应商', '发货地',
    '材质', '图片链接', '产品链接',
    '热门', '新品', '首次发现'
  ];
  const rows = data.map(p => [
    p.name, p.price, p.currency, extractCountry(p.category), extractType(p.category),
    (p.category || '').replace(/TYPE:\S+/g, '').replace(/ \| /g, ' ').trim(),
    p.delivery_days, p.suppliers?.name, p.suppliers?.shipping_from,
    (p.material_tags || []).join(';'), p.image_url, p.product_url,
    p.is_hot ? '是' : '', p.is_new ? '是' : '',
    p.first_seen_at
  ]);

  const csv = [
    '﻿' + headers.join(','),
    ...rows.map(r => r.map(c => {
      const v = (c ?? '').toString();
      return v.includes(',') || v.includes('"') ? `"${v.replace(/"/g, '""')}"` : v;
    }).join(','))
  ].join('\n');

  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="products.csv"');
  res.send(csv);
};
