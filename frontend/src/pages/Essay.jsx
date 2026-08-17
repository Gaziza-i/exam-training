import { useState } from "react";
import EssayForm from "../components/EssayForm.jsx";

const TABS = [
  { key: "ege", label: "Сочинение ЕГЭ" },
  { key: "final", label: "Итоговое сочинение" },
];

export default function Essay() {
  const [tab, setTab] = useState("ege");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Тренажёр сочинения</h1>
        <p className="text-sm text-slate-500 mt-1">
          У ЕГЭ (задание 27) и итогового сочинения разные критерии оценивания и разные типы заданий —
          пишите и проверяйте себя отдельно для каждого вида.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              tab === t.key
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Обе формы остаются смонтированными, чтобы черновик не терялся при переключении вкладок. */}
      <div className={tab === "ege" ? "" : "hidden"}>
        <EssayForm essayType="ege" />
      </div>
      <div className={tab === "final" ? "" : "hidden"}>
        <EssayForm essayType="final" />
      </div>
    </div>
  );
}
