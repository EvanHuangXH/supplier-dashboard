export default function CompareTable({ products, onClose }) {
  if (products.length < 2) return null;

  const rows = [
    { label: '价格', key: 'price', format: (v, p) => `¥${Number(v).toFixed(2)}${p.price_unit ? '/' + p.price_unit : ''}` },
    { label: '交期', key: 'delivery_days', format: (v) => v ? `${v}天` : '—' },
    { label: '材质', key: 'material_tags', format: (v) => (v || []).join('、') || '—' },
    { label: '发货地', key: 'suppliers.shipping_from', format: (v) => v || '—' },
    { label: '供应商', key: 'suppliers.name', format: (v) => v || '—' },
    { label: '热门', key: 'is_hot', format: (v) => v ? '🔥 是' : '否' },
    { label: '上线日期', key: 'listed_at', format: (v) => v || '—' },
  ];

  const getNested = (obj, path) => path.split('.').reduce((o, k) => (o || {})[k], obj);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] overflow-auto p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">产品对比</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="text-left p-2 bg-gray-50">对比项</th>
              {products.map(p => (
                <th key={p.id} className="text-left p-2 bg-gray-50">{p.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={row.key} className="border-t">
                <td className="p-2 font-medium text-gray-600">{row.label}</td>
                {products.map(p => (
                  <td key={p.id} className="p-2">
                    {row.format(getNested(p, row.key), p)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
