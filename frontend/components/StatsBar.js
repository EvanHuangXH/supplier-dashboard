export default function StatsBar({ stats }) {
  if (!stats) return null;

  return (
    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
      <span>📊 总产品 <strong>{stats.total_products}</strong></span>
      <span>🆕 今日新品 <strong>{stats.new_today}</strong></span>
      <span>🔥 热门 <strong>{stats.hot_products}</strong></span>
      <span>✅ {stats.active_suppliers} 家在线</span>
    </div>
  );
}
