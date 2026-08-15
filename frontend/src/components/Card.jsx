export default function Card({ children, className = "" }) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}
