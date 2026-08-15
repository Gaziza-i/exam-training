import { useEffect, useState } from "react";
import { api } from "../api.js";
import Card from "../components/Card.jsx";

export default function Essay() {
  const [criteria, setCriteria] = useState([]);
  const [essayId, setEssayId] = useState(null);
  const [sourceText, setSourceText] = useState("");
  const [essayText, setEssayText] = useState("");
  const [checklist, setChecklist] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    api.essayCriteria().then(setCriteria);
  }, []);

  const wordCount = essayText.trim() ? essayText.trim().split(/\s+/).length : 0;
  const checkedCount = Object.values(checklist).filter(Boolean).length;

  const save = async () => {
    setSaving(true);
    const payload = { source_text: sourceText, essay_text: essayText, checklist };
    try {
      if (essayId) {
        await api.updateEssay(essayId, payload);
      } else {
        const created = await api.createEssay(payload);
        setEssayId(created.id);
      }
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  };

  const toggle = (code) =>
    setChecklist((c) => ({ ...c, [code]: !c[code] }));

  return (
    <div className="grid lg:grid-cols-[1fr_320px] gap-4">
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Тренажёр сочинения</h1>

        <Card>
          <label className="text-xs font-medium text-slate-500 mb-1 block">
            Исходный текст (опционально — вставьте текст для сочинения)
          </label>
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent text-sm"
            placeholder="Текст для чтения…"
          />
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-medium text-slate-500">Ваше сочинение</label>
            <span className="text-xs text-slate-400">{wordCount} слов</span>
          </div>
          <textarea
            value={essayText}
            onChange={(e) => setEssayText(e.target.value)}
            rows={16}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent text-sm leading-relaxed"
            placeholder="Начните писать здесь…"
          />
          <div className="flex items-center justify-between mt-3">
            <button
              onClick={save}
              disabled={saving || !essayText.trim()}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? "Сохранение…" : "Сохранить черновик"}
            </button>
            {savedAt && (
              <span className="text-xs text-slate-400">
                Сохранено в {savedAt.toLocaleTimeString()}
              </span>
            )}
          </div>
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <h2 className="font-medium mb-1">Чек-лист критериев</h2>
          <p className="text-xs text-slate-500 mb-3">
            {checkedCount} из {criteria.length} — самопроверка перед отправкой
          </p>
          <div className="space-y-2">
            {criteria.map((c) => (
              <label
                key={c.code}
                className="flex items-start gap-2 text-sm cursor-pointer"
              >
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={!!checklist[c.code]}
                  onChange={() => toggle(c.code)}
                />
                <span>
                  <b>{c.code}.</b> {c.title}
                </span>
              </label>
            ))}
            {criteria.length === 0 && (
              <p className="text-sm text-slate-400">Загрузка критериев…</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
