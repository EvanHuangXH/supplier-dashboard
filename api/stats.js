const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { supplier_id } = req.query;

  const queries = [
    supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true),
    supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_new', true),
    supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_hot', true),
    supabase.from('suppliers').select('*').eq('status', 'active'),
    supabase.from('products').select('category').eq('is_active', true).not('category', 'is', null),
    supabase.from('products').select('shipping_country').eq('is_active', true).not('shipping_country', 'is', null),
    supabase.from('products').select('product_type').eq('is_active', true).not('product_type', 'is', null),
  ];

  // If supplier filter is active, scope country/type queries to that supplier
  if (supplier_id) {
    queries[0] = queries[0].eq('supplier_id', parseInt(supplier_id));
    queries[1] = queries[1].eq('supplier_id', parseInt(supplier_id));
    queries[2] = queries[2].eq('supplier_id', parseInt(supplier_id));
    queries[4] = queries[4].eq('supplier_id', parseInt(supplier_id));
    queries[5] = queries[5].eq('supplier_id', parseInt(supplier_id));
    queries[6] = queries[6].eq('supplier_id', parseInt(supplier_id));
  }

  const [
    { count: total },
    { count: newToday },
    { count: hot },
    { data: suppliers },
    { data: categories },
    { data: countries },
    { data: types },
  ] = await Promise.all(queries);

  // Count products per category
  const catCounts = {};
  (categories || []).forEach(p => {
    if (p.category) catCounts[p.category] = (catCounts[p.category] || 0) + 1;
  });

  // Count products per country
  const countryCounts = {};
  (countries || []).forEach(p => {
    if (p.shipping_country) countryCounts[p.shipping_country] = (countryCounts[p.shipping_country] || 0) + 1;
  });

  // Count products per type
  const typeCounts = {};
  (types || []).forEach(p => {
    if (p.product_type) typeCounts[p.product_type] = (typeCounts[p.product_type] || 0) + 1;
  });

  return res.json({
    total_products: total || 0,
    new_today: newToday || 0,
    hot_products: hot || 0,
    active_suppliers: (suppliers || []).length,
    suppliers: suppliers || [],
    categories: Object.entries(catCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count),
    countries: Object.entries(countryCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count),
    types: Object.entries(typeCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count),
  });
};
