import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { supabase } from '../lib/supabase';
import SearchBar from '../components/SearchBar';
import FilterPanel from '../components/FilterPanel';
import ProductGrid from '../components/ProductGrid';
import StatsBar from '../components/StatsBar';
import Pagination from '../components/Pagination';
import ExportButton from '../components/ExportButton';

export default function Home() {
  const router = useRouter();
  const [products, setProducts] = useState([]);
  const [stats, setStats] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [totalPages, setTotalPages] = useState(0);

  const [filters, setFilters] = useState({
    q: '',
    category: null,
    supplier_id: null,
    sort: 'listed_at_desc',
    is_hot: null,
    is_new: null,
    page: 1,
  });

  // Fetch stats
  useEffect(() => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(data => {
        setStats(data);
        setSuppliers(data.suppliers || []);
        setCategories(data.categories || []);
      })
      .catch(console.error);
  }, []);

  // Fetch products
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== null && v !== '' && v !== undefined) params.set(k, v);
      });

      const res = await fetch(`/api/search?${params}`);
      const data = await res.json();
      setProducts(data.products || []);
      setTotalPages(data.total_pages || 0);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  // Compare selection
  const handleCheck = (id, checked) => {
    const next = new Set(selected);
    if (checked) {
      if (next.size >= 4) {
        alert('最多选择4个产品进行对比');
        return;
      }
      next.add(id);
    } else {
      next.delete(id);
    }
    setSelected(next);
  };

  const handleCompare = () => {
    if (selected.size < 2) {
      alert('请至少选择2个产品进行对比');
      return;
    }
    router.push(`/compare?ids=${Array.from(selected).join(',')}`);
  };

  return (
    <div className="max-w-7xl mx-auto p-4">
      <h1 className="text-xl font-bold mb-4">🛒 供应商产品看板</h1>

      {/* Stats bar */}
      <div className="mb-4">
        <StatsBar stats={stats} />
      </div>

      {/* Search + Compare */}
      <div className="flex gap-4 mb-4">
        <div className="flex-1">
          <SearchBar onSearch={(q) => setFilters(f => ({ ...f, q, page: 1 }))} />
        </div>
        {selected.size >= 2 && (
          <button
            onClick={handleCompare}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 whitespace-nowrap"
          >
            📊 对比 ({selected.size})
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="mb-4">
        <FilterPanel
          filters={filters}
          onFilter={setFilters}
          suppliers={suppliers}
          categories={categories}
        />
      </div>

      {/* Products */}
      <ProductGrid
        products={products}
        selected={selected}
        onCheck={handleCheck}
        loading={loading}
      />

      {/* Pagination */}
      <div className="flex justify-between items-center mt-6">
        <Pagination page={filters.page} totalPages={totalPages} onPage={(p) => setFilters(f => ({ ...f, page: p }))} />
        <ExportButton filters={filters} />
      </div>
    </div>
  );
}
