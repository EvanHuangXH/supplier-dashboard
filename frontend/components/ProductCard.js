export default function ProductCard({ product, checked, onCheck, onCompare }) {
  return (
    <div className="border rounded-lg p-4 hover:shadow-lg transition-shadow bg-white">
      {/* Checkbox for compare */}
      <div className="flex items-center gap-2 mb-2">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onCheck(product.id, e.target.checked)}
          className="rounded"
        />
        <span className="text-xs text-gray-400">对比</span>
      </div>

      {/* Hot badge */}
      {product.is_hot && (
        <span className="inline-block bg-red-500 text-white text-xs px-2 py-0.5 rounded-full mb-2">
          🔥 热门
        </span>
      )}

      {/* New badge */}
      {product.is_new && (
        <span className="inline-block bg-green-500 text-white text-xs px-2 py-0.5 rounded-full mb-2 ml-1">
          新品
        </span>
      )}

      {/* Product image */}
      {product.image_url && (
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-40 object-cover rounded mb-3"
          loading="lazy"
          onError={(e) => { e.target.style.display = 'none'; }}
        />
      )}

      {/* Product name */}
      <h3 className="font-semibold text-sm mb-2 line-clamp-2">{product.name}</h3>

      {/* Price */}
      {product.price && (
        <p className="text-lg font-bold text-blue-600">
          ¥{Number(product.price).toFixed(2)}
          {product.price_unit && <span className="text-sm font-normal text-gray-500">/{product.price_unit}</span>}
        </p>
      )}

      {/* Delivery & shipping */}
      <div className="text-xs text-gray-500 mt-1 space-y-0.5">
        {product.delivery_days && <p>🚚 交期 {product.delivery_days}天</p>}
        {product.suppliers?.shipping_from && <p>📍 {product.suppliers.shipping_from}</p>}
        {product.listed_at && <p>📅 上线 {product.listed_at}</p>}
      </div>

      {/* Material tags */}
      {product.material_tags && product.material_tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {product.material_tags.map((tag, i) => (
            <span key={i} className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{tag}</span>
          ))}
        </div>
      )}

      {/* Supplier link */}
      <a
        href={product.product_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block mt-2 text-xs text-blue-500 hover:underline"
      >
        🏪 {product.suppliers?.name} →
      </a>
    </div>
  );
}
