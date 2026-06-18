import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // Today in UTC for first_seen_at comparison
  const today = new Date().toISOString().slice(0, 10); // "2026-06-16"

  const [
    { count: total },
    { count: newToday },
    { count: hot },
    { data: suppliers },
    { data: categories },
  ] = await Promise.all([
    supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true),
    supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_active', true).gte('first_seen_at', today),
    supabase.from('products').select('*', { count: 'exact', head: true }).eq('is_hot', true),
    supabase.from('suppliers').select('*').eq('status', 'active'),
    supabase.from('products').select('category').eq('is_active', true).not('category', 'is', null),
  ]);

  const catCounts = {};
  (categories || []).forEach(p => {
    if (p.category) catCounts[p.category] = (catCounts[p.category] || 0) + 1;
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
  });
}
