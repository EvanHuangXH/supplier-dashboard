const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// Helper: paginate through all rows to bypass Supabase 1000-row limit
async function fetchAll(column, supplierId) {
  const PAGE = 1000;
  const MAX = 20000;
  let all = [];
  for (let offset = 0; offset < MAX; offset += PAGE) {
    let q = supabase.from('products').select(column).eq('is_active', true);
    if (supplierId) q = q.eq('supplier_id', parseInt(supplierId));
    const { data, error } = await q.range(offset, offset + PAGE - 1);
    if (error || !data || data.length === 0) break;
    all = all.concat(data);
    if (data.length < PAGE) break;
  }
  return all;
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { supplier_id } = req.query;
  const sid = supplier_id ? parseInt(supplier_id) : null;

  // Base queries for totals
  let totalQ = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true);
  let newQ = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_new', true);
  let hotQ = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_hot', true);
  if (sid) {
    totalQ = totalQ.eq('supplier_id', sid);
    newQ = newQ.eq('supplier_id', sid);
    hotQ = hotQ.eq('supplier_id', sid);
  }

  const [
    { count: total },
    { count: newToday },
    { count: hot },
    { data: suppliers },
    categories,
    countries,
    types,
  ] = await Promise.all([
    totalQ,
    newQ,
    hotQ,
    supabase.from('suppliers').select('*').eq('status', 'active'),
    fetchAll('category', sid),
    fetchAll('shipping_country', sid),
    fetchAll('product_type', sid),
  ]);

  const countBy = (arr, key) => {
    const m = {};
    arr.forEach(p => { if (p[key]) m[p[key]] = (m[p[key]] || 0) + 1; });
    return Object.entries(m).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
  };

  return res.json({
    total_products: total || 0,
    new_today: newToday || 0,
    hot_products: hot || 0,
    active_suppliers: (suppliers || []).length,
    suppliers: suppliers || [],
    categories: countBy(categories, 'category'),
    countries: countBy(countries, 'shipping_country'),
    types: countBy(types, 'product_type'),
  });
};
