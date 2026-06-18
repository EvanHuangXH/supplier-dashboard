import { useState } from 'react';

export default function ExportButton({ filters }) {
  const [exporting, setExporting] = useState(false);
  const [open, setOpen] = useState(false);

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
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={exporting}
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-warm-200 rounded-xl text-sm font-medium text-warm-600 hover:border-warm-300 hover:bg-warm-50 active:scale-95 transition-all duration-200 disabled:opacity-50"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {exporting ? '导出中...' : '导出'}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1.5 z-20 bg-white border border-warm-200 rounded-xl shadow-lg overflow-hidden min-w-[160px]">
            <button
              onClick={() => handleExport('csv')}
              className="flex items-center gap-2 w-full text-left px-4 py-2.5 text-sm text-warm-700 hover:bg-warm-50 transition-colors"
            >
              <span className="text-base">📊</span> CSV (Excel)
            </button>
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-2 w-full text-left px-4 py-2.5 text-sm text-warm-700 hover:bg-warm-50 transition-colors border-t border-warm-100"
            >
              <span className="text-base">📋</span> JSON
            </button>
          </div>
        </>
      )}
    </div>
  );
}
