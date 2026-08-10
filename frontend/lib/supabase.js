import { createClient } from '@supabase/supabase-js';

let _supabase = null;

function getSupabase() {
  if (!_supabase) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key || url.startsWith('[SENSITIVE')) {
      // During vercel build, sensitive env vars are redacted.
      // Return a dummy client; real values are available at runtime on Vercel.
      console.warn('Supabase credentials not available at build time, deferring to runtime');
      return null;
    }
    _supabase = createClient(url, key);
  }
  return _supabase;
}

export const supabase = new Proxy({}, {
  get(_, prop) {
    const client = getSupabase();
    if (!client) throw new Error('Supabase client not available — credentials missing');
    const val = client[prop];
    return typeof val === 'function' ? val.bind(client) : val;
  }
});
