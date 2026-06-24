export default function FilterPanel({ filters, onFilter, suppliers, categories, countries, types }) {
  const handleChange = (key, value) => {
    onFilter({ ...filters, [key]: value, page: 1 });
  };

  const selectClass = "px-3 py-2 bg-white border border-warm-200 rounded-xl text-sm text-warm-700 focus:outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 transition-all duration-200 cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2378716C%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22/%3E%3C/svg%3E')] bg-[length:12px] bg-[right_8px_center] bg-no-repeat pr-8";

  const hasActiveFilters = filters.supplier_id || filters.category || filters.is_hot === 'true' || filters.is_new === 'true';

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {/* Supplier filter */}
      <select
        value={filters.supplier_id || ''}
        onChange={(e) => {
          const newId = e.target.value || null;
          onFilter({ ...filters, supplier_id: newId, category: null, page: 1 });
        }}
        className={selectClass}
      >
        <option value="">全部供应商</option>
        {(suppliers || []).map(s => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      {/* Country filter */}
      {countries && countries.length > 0 && (
        <select
          value={filters.shipping_country || ''}
          onChange={(e) => handleChange('shipping_country', e.target.value || null)}
          className={selectClass}
        >
          <option value="">全部国家</option>
          {countries.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      )}

      {/* Product Type filter */}
      {types && types.length > 0 && (
        <select
          value={filters.product_type || ''}
          onChange={(e) => handleChange('product_type', e.target.value || null)}
          className={selectClass}
        >
          <option value="">全部类型</option>
          {types.map(t => (
            <option key={t.name} value={t.name}>{t.name} ({t.count})</option>
          ))}
        </select>
      )}

      {/* Category filter */}
      {categories && categories.length > 0 && (
        <select
          value={filters.category || ''}
          onChange={(e) => handleChange('category', e.target.value || null)}
          className={selectClass}
        >
          <option value="">全部分类</option>
          {categories.map(c => (
            <option key={c.name} value={c.name}>{c.name} ({c.count})</option>
          ))}
        </select>
      )}

      {/* Sort */}
      <select
        value={filters.sort || 'listed_at_desc'}
        onChange={(e) => handleChange('sort', e.target.value)}
        className={selectClass}
      >
        <option value="first_seen_at_desc">最新发现 ↓</option>
        <option value="first_seen_at_asc">最早发现 ↑</option>
        <option value="price_asc">价格低 → 高</option>
        <option value="price_desc">价格高 → 低</option>
      </select>

      {/* Divider */}
      <span className="w-px h-5 bg-warm-200 mx-1" />

      {/* Hot toggle */}
      <button
        onClick={() => handleChange('is_hot', filters.is_hot === 'true' ? null : 'true')}
        className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
          filters.is_hot === 'true'
            ? 'bg-rose-50 text-rose-700 border border-rose-200 shadow-sm'
            : 'bg-white text-warm-500 border border-warm-200 hover:border-rose-200 hover:text-rose-600'
        }`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${filters.is_hot === 'true' ? 'bg-rose-500' : 'bg-warm-300'}`} />
        热门
      </button>

      {/* New toggle */}
      <button
        onClick={() => handleChange('is_new', filters.is_new === 'true' ? null : 'true')}
        className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
          filters.is_new === 'true'
            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-sm'
            : 'bg-white text-warm-500 border border-warm-200 hover:border-emerald-200 hover:text-emerald-600'
        }`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${filters.is_new === 'true' ? 'bg-emerald-500' : 'bg-warm-300'}`} />
        新品
      </button>

      {/* Clear filters */}
      {hasActiveFilters && (
        <button
          onClick={() => onFilter({ q: filters.q, category: null, supplier_id: null, shipping_country: null, sort: 'first_seen_at_desc', is_hot: null, is_new: null, page: 1 })}
          className="inline-flex items-center gap-1 px-2.5 py-2 text-xs text-warm-400 hover:text-warm-600 transition-colors"
        >
          清除筛选
        </button>
      )}
    </div>
  );
}
