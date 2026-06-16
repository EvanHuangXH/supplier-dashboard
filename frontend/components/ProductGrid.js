import ProductCard from './ProductCard';

export default function ProductGrid({ products, selected, onCheck, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border rounded-lg p-4 animate-pulse">
            <div className="bg-gray-200 h-40 rounded mb-3"></div>
            <div className="bg-gray-200 h-4 w-3/4 mb-2"></div>
            <div className="bg-gray-200 h-6 w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg">暂无匹配产品</p>
        <p className="text-sm mt-1">试试调整筛选条件</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {products.map(product => (
        <ProductCard
          key={product.id}
          product={product}
          checked={selected.has(product.id)}
          onCheck={onCheck}
        />
      ))}
    </div>
  );
}
