export default function AccuracyBar({ accuracy }) {
  if (accuracy === null || accuracy === undefined) {
    return <span className="text-xs text-slate-400">нет попыток</span>;
  }
  const color =
    accuracy >= 80 ? "bg-emerald-500" : accuracy >= 50 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="h-2 flex-1 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${accuracy}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400 w-10 text-right">
        {accuracy}%
      </span>
    </div>
  );
}
