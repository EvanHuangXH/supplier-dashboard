import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// Single pagination pass: fetch category, country, type in one go
async function fetchAllThree(supplierId) {
  const PAGE = 1000, MAX = 20000;
  const cats = [], countries = [], types = [];
  for (let offset = 0; offset < MAX; offset += PAGE) {
    let q = supabase.from('products')
      .select('category,shipping_country,product_type')
      .eq('is_active', true);
    if (supplierId) q = q.eq('supplier_id', parseInt(supplierId));
    const { data, error } = await q.range(offset, offset + PAGE - 1);
    if (error || !data || data.length === 0) break;
    for (const p of data) {
      cats.push({ category: p.category });
      countries.push({ shipping_country: p.shipping_country });
      types.push({ product_type: p.product_type });
    }
    if (data.length < PAGE) break;
  }
  return { cats, countries, types };
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { supplier_id } = req.query;
  const sid = supplier_id ? parseInt(supplier_id) : null;

  let baseQ = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true);
  let newQ = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true).eq('is_new', true);
  let hotQ = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true).eq('is_hot', true);
  if (sid) { baseQ = baseQ.eq('supplier_id', sid); newQ = newQ.eq('supplier_id', sid); hotQ = hotQ.eq('supplier_id', sid); }

  const [
    { count: total },
    { count: newToday },
    { count: hot },
    { data: suppliers },
    { cats, countries, types },
  ] = await Promise.all([baseQ, newQ, hotQ, supabase.from('suppliers').select('*').eq('status', 'active'), fetchAllThree(sid)]);

  const countBy = (arr, key) => {
    const m = {};
    arr.forEach(p => { if (p[key]) m[p[key]] = (m[p[key]] || 0) + 1; });
    return Object.entries(m).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
  };

  // Countries: return as strings for FilterPanel compatibility
  const countryNames = [...new Set(countries.map(p => p.shipping_country).filter(Boolean))].sort();

  return res.json({
    total_products: total || 0,
    new_today: newToday || 0,
    hot_products: hot || 0,
    active_suppliers: (suppliers || []).length,
    suppliers: suppliers || [],
    categories: countBy(cats, 'category'),
    countries: countryNames,
    types: countBy(types, 'product_type'),
  });
}
