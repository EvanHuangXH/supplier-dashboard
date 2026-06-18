export default function Pagination({ page, totalPages, onPage }) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 bg-white border border-warm-200 rounded-lg text-sm text-warm-600 hover:bg-warm-50 hover:border-warm-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
      >
        ← 上一页
      </button>

      {/* Page numbers */}
      <div className="flex items-center gap-1">
        {Array.from({ length: totalPages }, (_, i) => i + 1)
          .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
          .reduce((acc, p, idx, arr) => {
            if (idx > 0 && p - arr[idx - 1] > 1) {
              acc.push('...');
            }
            acc.push(p);
            return acc;
          }, [])
          .map((p, i) =>
            p === '...' ? (
              <span key={`dots-${i}`} className="px-1 text-warm-300">…</span>
            ) : (
              <button
                key={p}
                onClick={() => onPage(p)}
                className={`w-8 h-8 rounded-lg text-sm font-medium transition-all duration-200 ${
                  p === page
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-white border border-warm-200 text-warm-600 hover:bg-warm-50'
                }`}
              >
                {p}
              </button>
            )
          )}
      </div>

      <button
        onClick={() => onPage(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 bg-white border border-warm-200 rounded-lg text-sm text-warm-600 hover:bg-warm-50 hover:border-warm-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
      >
        下一页 →
      </button>
    </div>
  );
}
