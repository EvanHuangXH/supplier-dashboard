export default function FilterPanel({ filters, onFilter, suppliers, categories }) {
  const handleChange = (key, value) => {
    onFilter({ ...filters, [key]: value, page: 1 });
  };

  return (
    <div className="flex flex-wrap gap-3 items-center">
      {/* Supplier filter */}
      <select
        value={filters.supplier_id || ''}
        onChange={(e) => handleChange('supplier_id', e.target.value || null)}
        className="px-3 py-2 border rounded-lg text-sm"
      >
        <option value="">全部供应商</option>
        {(suppliers || []).map(s => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      {/* Category filter */}
      <select
        value={filters.category || ''}
        onChange={(e) => handleChange('category', e.target.value || null)}
        className="px-3 py-2 border rounded-lg text-sm"
      >
        <option value="">全部分类</option>
        {(categories || []).map(c => (
          <option key={c.name} value={c.name}>{c.name} ({c.count})</option>
        ))}
      </select>

      {/* Sort */}
      <select
        value={filters.sort || 'listed_at_desc'}
        onChange={(e) => handleChange('sort', e.target.value)}
        className="px-3 py-2 border rounded-lg text-sm"
      >
        <option value="listed_at_desc">上新时间 ↓</option>
        <option value="listed_at_asc">上新时间 ↑</option>
        <option value="price_asc">价格 ↑</option>
        <option value="price_desc">价格 ↓</option>
      </select>

      {/* Hot toggle */}
      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={filters.is_hot === 'true'}
          onChange={(e) => handleChange('is_hot', e.target.checked ? 'true' : null)}
          className="rounded"
        />
        🔥 仅热门
      </label>

      {/* New toggle */}
      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={filters.is_new === 'true'}
          onChange={(e) => handleChange('is_new', e.target.checked ? 'true' : null)}
          className="rounded"
        />
        🆕 仅新品
      </label>
    </div>
  );
}
