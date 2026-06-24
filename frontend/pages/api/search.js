import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { q, category, supplier_id, shipping_country, min_price, max_price, shipping_from, date_from, date_to, is_hot, is_new, sort = 'first_seen_at_desc', page = 1, limit = 20 } = req.query;
  const offset = (parseInt(page) - 1) * parseInt(limit);

  let query = supabase
    .from('products')
    .select('*, suppliers!inner(name, website, shipping_from)', { count: 'exact' })
    .eq('is_active', true);

  if (q) query = query.or(`name.ilike.%${q}%,description.ilike.%${q}%`);
  if (category) query = query.eq('category', category);
  if (supplier_id) query = query.eq('supplier_id', parseInt(supplier_id));
  if (shipping_country) query = query.like('category', `%${shipping_country}%`);
  if (req.query.product_type) query = query.like('category', `%TYPE:${req.query.product_type}%`);
  if (min_price) query = query.gte('price', parseFloat(min_price));
  if (max_price) query = query.lte('price', parseFloat(max_price));
  if (shipping_from) query = query.eq('suppliers.shipping_from', shipping_from);
  if (date_from) query = query.gte('listed_at', date_from);
  if (date_to) query = query.lte('listed_at', date_to);
  if (is_hot === 'true') query = query.eq('is_hot', true);
  if (is_new === 'true') {
    // "新品" = first seen today (UTC)
    const today = new Date().toISOString().slice(0, 10);
    query = query.gte('first_seen_at', today);
  }

  // Default sort: newest first_seen
  const sortMap = {
    first_seen_at_desc: ['first_seen_at', { ascending: false }],
    first_seen_at_asc: ['first_seen_at', { ascending: true }],
    listed_at_desc: ['listed_at', { ascending: false }],
    listed_at_asc: ['listed_at', { ascending: true }],
    price_asc: ['price', { ascending: true }],
    price_desc: ['price', { ascending: false }],
  };
  const defaultSort = 'first_seen_at_desc';
  const [sortCol, sortOpts] = sortMap[sort] || sortMap[defaultSort];
  query = query.order(sortCol, sortOpts);
  query = query.range(offset, offset + parseInt(limit) - 1);

  const { data, error, count } = await query;
  if (error) return res.status(500).json({ error: error.message });

  return res.json({ products: data, total: count, page: parseInt(page), total_pages: Math.ceil(count / parseInt(limit)) });
}
