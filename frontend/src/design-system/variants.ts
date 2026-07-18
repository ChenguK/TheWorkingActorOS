export const variants = {
  card: "min-w-0 max-w-full overflow-hidden rounded-md border border-slate-200 bg-white p-3 shadow-sm",
  compactRow: "min-w-0 max-w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left shadow-sm",
  panel: "min-w-0 max-w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm",
  notice: {
    neutral: "rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700",
    info: "rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900",
    success: "rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800",
    warning: "rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900",
    danger: "rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700"
  },
  link: "font-semibold text-accent hover:underline"
} as const;
