import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { supplier_id } = req.query;
  const today = new Date().toISOString().slice(0, 10);

  // Base query filter
  let baseQuery = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true);
  let catQuery = supabase.from('products').select('category').eq('is_active', true).not('category', 'is', null);
  let newQuery = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true).gte('first_seen_at', today);
  let hotQuery = supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_hot', true);

  if (supplier_id) {
    baseQuery = baseQuery.eq('supplier_id', parseInt(supplier_id));
    catQuery = catQuery.eq('supplier_id', parseInt(supplier_id));
    newQuery = newQuery.eq('supplier_id', parseInt(supplier_id));
    hotQuery = hotQuery.eq('supplier_id', parseInt(supplier_id));
  }

  const [
    { count: total },
    { count: newToday },
    { count: hot },
    { data: suppliers },
    { data: categories },
  ] = await Promise.all([
    baseQuery,
    newQuery,
    hotQuery,
    supabase.from('suppliers').select('*').eq('status', 'active'),
    catQuery,
  ]);

  const catCounts = {};
  const countrySet = new Set();
  (categories || []).forEach(p => {
    if (p.category) {
      catCounts[p.category] = (catCounts[p.category] || 0) + 1;
      // Extract country from category field
      const countries = ['美国','加拿大','墨西哥','英国','德国','法国','澳大利亚','日本','韩国','意大利','西班牙','荷兰','巴西','中国'];
      for (const c of countries) {
        if (p.category.includes(c)) countrySet.add(c);
      }
    }
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
    countries: Array.from(countrySet).sort(),
  });
}
