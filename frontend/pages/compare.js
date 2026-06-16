import { useRouter } from 'next/router';
import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import CompareTable from '../components/CompareTable';

export default function ComparePage() {
  const router = useRouter();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ids = (router.query.ids || '').split(',').filter(Boolean);
    if (ids.length === 0) { setLoading(false); return; }

    supabase
      .from('products')
      .select('*, suppliers!inner(name, website, shipping_from)')
      .in('id', ids)
      .then(({ data }) => {
        setProducts(data || []);
        setLoading(false);
      });
  }, [router.query.ids]);

  if (loading) return <div className="p-8 text-center">加载中...</div>;
  if (products.length < 2) return <div className="p-8 text-center text-gray-500">请选择 2-4 个产品进行对比</div>;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <CompareTable products={products} onClose={() => router.push('/')} />
    </div>
  );
}
