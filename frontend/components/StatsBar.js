export default function StatsBar({ stats }) {
  if (!stats) return <StatsSkeleton />;

  const items = [
    { label: '总产品', value: stats.total_products, icon: '📦', gradient: 'from-brand-50 to-brand-100/50', text: 'text-brand-700' },
    { label: '今日新品', value: stats.new_today, icon: '✨', gradient: 'from-amber-50 to-amber-100/50', text: 'text-amber-700' },
    { label: '热门产品', value: stats.hot_products, icon: '🔥', gradient: 'from-rose-50 to-rose-100/50', text: 'text-rose-700' },
    { label: '在线供应商', value: stats.active_suppliers, icon: '🏪', gradient: 'from-emerald-50 to-emerald-100/50', text: 'text-emerald-700' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
      {items.map((item) => (
        <div
          key={item.label}
          className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${item.gradient} p-4 md:p-5 shadow-card border border-white/60`}
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-warm-500 tracking-wide uppercase">{item.label}</p>
              <p className={`text-2xl md:text-3xl font-display font-bold tabular-nums mt-1 ${item.text}`}>
                {item.value.toLocaleString()}
              </p>
            </div>
            <span className="text-2xl opacity-60">{item.icon}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="rounded-xl bg-white p-4 md:p-5 shadow-card">
          <div className="skeleton h-3 w-16 mb-2" />
          <div className="skeleton h-8 w-20" />
        </div>
      ))}
    </div>
  );
}
