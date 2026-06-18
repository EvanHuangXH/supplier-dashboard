import ProductCard from './ProductCard';

function SkeletonCard() {
  return (
    <div className="card overflow-hidden">
      <div className="aspect-[4/3] skeleton rounded-none" />
      <div className="p-4 space-y-3">
        <div className="skeleton h-3 w-16" />
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
        <div className="skeleton h-6 w-24" />
        <div className="flex gap-1">
          <div className="skeleton h-5 w-12 rounded-md" />
          <div className="skeleton h-5 w-12 rounded-md" />
          <div className="skeleton h-5 w-12 rounded-md" />
        </div>
      </div>
    </div>
  );
}

function EmptyState({ hasFilters }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
      <span className="text-5xl mb-4">
        {hasFilters ? '🔍' : '📦'}
      </span>
      <h3 className="text-lg font-display font-semibold text-warm-700 mb-1">
        {hasFilters ? '没有匹配的产品' : '还没有产品'}
      </h3>
      <p className="text-sm text-warm-400 max-w-sm">
        {hasFilters
          ? '试试调整筛选条件或搜索关键词'
          : '产品数据正在采集中，稍后回来查看'}
      </p>
    </div>
  );
}

export default function ProductGrid({ products, selected, onCheck, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (!products || products.length === 0) {
    return <EmptyState hasFilters={false} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {products.map((product, i) => (
        <ProductCard
          key={product.id}
          product={product}
          checked={selected.has(product.id)}
          onCheck={onCheck}
          index={i}
        />
      ))}
    </div>
  );
}
