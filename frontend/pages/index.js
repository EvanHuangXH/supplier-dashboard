import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
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
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState('');

  const [filters, setFilters] = useState({
    q: '',
    category: null,
    supplier_id: null,
    sort: 'first_seen_at_desc',
    is_hot: null,
    is_new: null,
    page: 1,
  });

  // Fetch stats (re-fetch when supplier filter changes)
  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.supplier_id) params.set('supplier_id', filters.supplier_id);
    fetch(`/api/stats?${params}`)
      .then(r => r.json())
      .then(data => {
        setStats(data);
        setSuppliers(data.suppliers || []);
        setCategories(data.categories || []);
      })
      .catch(console.error);
  }, [filters.supplier_id]);

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

  const handleCheck = (id, checked) => {
    const next = new Set(selected);
    if (checked) {
      if (next.size >= 4) {
        return;
      }
      next.add(id);
    } else {
      next.delete(id);
    }
    setSelected(next);
  };

  const handleCompare = () => {
    if (selected.size < 2) return;
    router.push(`/compare?ids=${Array.from(selected).join(',')}`);
  };

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMsg('正在触发抓取...');
    try {
      const res = await fetch('/api/trigger-scrape', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setScrapeMsg('抓取已触发！约5分钟后开始，15-30分钟完成');
      } else {
        setScrapeMsg('触发失败：' + (data.error || '未知错误'));
      }
    } catch (e) {
      setScrapeMsg('网络错误，请重试');
    }
    setTimeout(() => { setScraping(false); setScrapeMsg(''); }, 8000);
  };

  const hasActiveFilters = filters.supplier_id || filters.category || filters.is_hot || filters.is_new || filters.q;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-lg border-b border-warm-100">
        <div className="max-w-[1440px] mx-auto px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg md:text-xl font-display font-bold text-warm-900 tracking-tight">
                供应商产品看板
              </h1>
              {stats && (
                <p className="text-xs text-warm-400 mt-0.5">
                  {stats.total_products.toLocaleString()} 个产品 · {stats.active_suppliers} 家供应商在线
                </p>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {/* Scrape button */}
              <button
                onClick={handleScrape}
                disabled={scraping}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 active:scale-95 transition-all duration-200 shadow-sm disabled:opacity-50"
              >
                <svg className={`w-4 h-4 ${scraping ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                一键抓取
              </button>

              {/* Compare button */}
              {selected.size >= 2 && (
                <button
                  onClick={handleCompare}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700 active:scale-95 transition-all duration-200 shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  对比 ({selected.size})
                </button>
              )}
            </div>

            {/* Scrape message */}
            {scrapeMsg && (
              <div className="fixed top-16 right-4 bg-white border border-emerald-200 shadow-lg rounded-xl px-4 py-3 text-sm text-emerald-700 z-50 animate-slide-up">
                {scrapeMsg}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-[1440px] mx-auto px-4 md:px-6 py-6">
        {/* Stats */}
        <section className="mb-6">
          <StatsBar stats={stats} />
        </section>

        {/* Search + Export */}
        <section className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="flex-1">
            <SearchBar onSearch={(q) => setFilters(f => ({ ...f, q, page: 1 }))} />
          </div>
          <ExportButton filters={filters} />
        </section>

        {/* Filters */}
        <section className="mb-6">
          <FilterPanel
            filters={filters}
            onFilter={setFilters}
            suppliers={suppliers}
            categories={categories}
          />
        </section>

        {/* Results summary */}
        {!loading && products.length > 0 && (
          <p className="text-xs text-warm-400 mb-3">
            {hasActiveFilters ? '筛选结果' : '全部产品'} · 第 {filters.page} 页
          </p>
        )}

        {/* Product grid */}
        <section className="min-h-[400px]">
          <ProductGrid
            products={products}
            selected={selected}
            onCheck={handleCheck}
            loading={loading}
          />
        </section>

        {/* Pagination */}
        {totalPages > 1 && (
          <section className="mt-8 flex justify-center">
            <Pagination page={filters.page} totalPages={totalPages} onPage={(p) => setFilters(f => ({ ...f, page: p }))} />
          </section>
        )}
      </main>
    </div>
  );
}
