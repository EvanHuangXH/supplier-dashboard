import { useState } from 'react';

export default function ProductCard({ product, checked, onCheck, index = 0 }) {
  const [imgError, setImgError] = useState(false);

  return (
    <div
      className="card group cursor-pointer animate-slide-up overflow-hidden"
      style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'both' }}
    >
      {/* Image area */}
      <div className="relative aspect-[4/3] bg-warm-100 overflow-hidden">
        {product.image_url && !imgError ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-warm-300 text-4xl">
            📦
          </div>
        )}

        {/* Badges */}
        <div className="absolute top-2 left-2 flex gap-1.5">
          {product.is_hot && (
            <span className="inline-flex items-center gap-1 bg-rose-500/90 backdrop-blur-sm text-white text-[11px] font-medium px-2 py-0.5 rounded-md">
              <span className="w-1 h-1 rounded-full bg-white animate-pulse" />
              热门
            </span>
          )}
          {product.is_new && (
            <span className="inline-flex items-center gap-1 bg-emerald-500/90 backdrop-blur-sm text-white text-[11px] font-medium px-2 py-0.5 rounded-md">
              <span className="w-1 h-1 rounded-full bg-white" />
              新品
            </span>
          )}
        </div>

        {/* Compare checkbox */}
        <label className="absolute top-2 right-2 flex items-center gap-1.5 bg-white/90 backdrop-blur-sm rounded-md px-2 py-1 text-[11px] text-warm-600 cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity duration-200 shadow-sm">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => onCheck(product.id, e.target.checked)}
            className="w-3 h-3 rounded accent-brand-600"
          />
          对比
        </label>
      </div>

      {/* Content */}
      <div className="p-3 md:p-4">
        {/* Supplier */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className="text-[10px] font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">
            {product.suppliers?.name}
          </span>
          {product.suppliers?.shipping_from && (
            <span className="text-[10px] text-warm-400">· {product.suppliers.shipping_from}</span>
          )}
        </div>

        {/* Category */}
        {product.category && (
          <span className="inline-block text-[10px] font-medium text-warm-500 bg-warm-50 px-1.5 py-0.5 rounded mb-1.5">
            {product.category}
          </span>
        )}

        {/* Name */}
        <h3 className="font-display font-semibold text-sm leading-snug mb-2 line-clamp-2 text-warm-800 group-hover:text-brand-700 transition-colors">
          {product.name}
        </h3>

        {/* Price */}
        <div className="flex items-baseline gap-1 mb-2">
          {product.price != null ? (
            <>
              <span className="text-lg font-display font-bold text-warm-900 tabular-nums">
                ¥{Number(product.price).toFixed(2)}
              </span>
              {product.price_unit && (
                <span className="text-xs text-warm-400">/{product.price_unit}</span>
              )}
            </>
          ) : (
            <span className="text-sm text-warm-400">价格待询</span>
          )}
        </div>

        {/* Meta info */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-warm-400">
          {product.delivery_days && (
            <span className="inline-flex items-center gap-1">
              <span className="w-1 h-1 rounded-full bg-emerald-400" />
              {product.delivery_days}天交货
            </span>
          )}
          {product.first_seen_at && (
            <span className="inline-flex items-center gap-1" title="首次发现时间">
              <span className="w-1 h-1 rounded-full bg-brand-400" />
              {product.first_seen_at.slice(0, 10)}
            </span>
          )}
        </div>

        {/* Material tags */}
        {product.material_tags && product.material_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2.5 pt-2.5 border-t border-warm-100">
            {product.material_tags.slice(0, 4).map((tag, i) => (
              <span key={i} className="text-[10px] text-warm-500 bg-warm-50 px-1.5 py-0.5 rounded-md">
                {tag}
              </span>
            ))}
            {product.material_tags.length > 4 && (
              <span className="text-[10px] text-warm-400">+{product.material_tags.length - 4}</span>
            )}
          </div>
        )}

        {/* Link */}
        <div className="flex items-center gap-2 mt-2.5">
          <a
            href={product.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-600 hover:text-brand-700 transition-colors"
          >
            查看详情
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </a>
          {product.product_url && product.product_url.includes('#product=') && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200" title="链接非真实产品页">
              ⚠
            </span>
          )}
          {(!product.image_url || product.image_url.includes('image-error')) && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-500 border border-red-200" title="图片缺失">
              🖼
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
