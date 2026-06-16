import { useState } from 'react';

export default function ExportButton({ filters }) {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const params = new URLSearchParams({ ...filters, format });
      const response = await fetch(`/api/export?${params}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `products.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('导出失败: ' + e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="relative inline-block group">
      <button className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
        📤 导出
      </button>
      <div className="absolute right-0 mt-1 bg-white border rounded-lg shadow-lg hidden group-hover:block z-10">
        <button
          onClick={() => handleExport('csv')}
          disabled={exporting}
          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
        >
          CSV (Excel)
        </button>
        <button
          onClick={() => handleExport('json')}
          disabled={exporting}
          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
        >
          JSON
        </button>
      </div>
    </div>
  );
}
