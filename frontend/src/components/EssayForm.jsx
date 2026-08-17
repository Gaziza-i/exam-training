import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import Card from "./Card.jsx";

const TYPE_CONFIG = {
  ege: {
    heading: "Сочинение ЕГЭ (задание 27)",
    sourceLabel: "Исходный текст (опционально — вставьте текст для сочинения)",
    sourcePlaceholder: "Текст для чтения…",
    essayPlaceholder: "Начните писать здесь…",
    minWords: 150,
    recommendedWords: "200–250",
  },
  final: {
    heading: "Итоговое сочинение",
    sourceLabel: "Тема / направление итогового сочинения",
    sourcePlaceholder:
      "Например: «Между прошлым и будущим: портрет моего поколения» или конкретная тема, выданная на экзамене…",
    essayPlaceholder: "Начните писать здесь… Не забудьте опереться минимум на одно литературное произведение.",
    minWords: 250,
    recommendedWords: "350+",
  },
};

// Итоговое сочинение оценивается «зачёт/незачёт»: обязательны требования 1-2,
// а из критериев 1-5 нужен «зачёт» минимум по трём, включая обязательные 1 и 2.
function finalVerdict(checklist) {
  const req1 = !!checklist.T1;
  const req2 = !!checklist.T2;
  if (!req1 || !req2) return { pass: false, label: "Незачёт — не выполнены требования 1–2" };
  const c1 = !!checklist.C1;
  const c2 = !!checklist.C2;
  const total = ["C1", "C2", "C3", "C4", "C5"].filter((c) => checklist[c]).length;
  const pass = c1 && c2 && total >= 3;
  if (pass) return { pass: true, label: "Зачёт" };
  if (!c1 || !c2) return { pass: false, label: "Незачёт — обязательны критерии 1 и 2" };
  return { pass: false, label: "Незачёт — нужно «зачёт» минимум по 3 критериям из 5" };
}

export default function EssayForm({ essayType }) {
  const cfg = TYPE_CONFIG[essayType];
  const [criteria, setCriteria] = useState([]);
  const [essayId, setEssayId] = useState(null);
  const [sourceText, setSourceText] = useState("");
  const [essayText, setEssayText] = useState("");
  const [checklist, setChecklist] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [ocrPreviewUrl, setOcrPreviewUrl] = useState(null);
  const [ocrText, setOcrText] = useState("");
  const [ocrError, setOcrError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api.essayCriteria(essayType).then(setCriteria);
  }, [essayType]);

  const wordCount = essayText.trim() ? essayText.trim().split(/\s+/).length : 0;
  const checkedCount = Object.values(checklist).filter(Boolean).length;
  const belowMin = wordCount > 0 && wordCount < cfg.minWords;

  const save = async () => {
    setSaving(true);
    const payload = { essay_type: essayType, source_text: sourceText, essay_text: essayText, checklist };
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

  const toggle = (code) => setChecklist((c) => ({ ...c, [code]: !c[code] }));

  const handlePhoto = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setOcrError(null);
    setOcrText("");
    setOcrProgress(0);
    setOcrPreviewUrl(URL.createObjectURL(file));
    setOcrBusy(true);
    try {
      const { createWorker } = await import("tesseract.js");
      const worker = await createWorker("rus", 1, {
        logger: (m) => {
          if (m.status === "recognizing text") setOcrProgress(Math.round(m.progress * 100));
        },
      });
      const { data } = await worker.recognize(file);
      await worker.terminate();
      const text = (data.text || "").trim();
      if (!text) {
        setOcrError("Не удалось распознать текст на фото. Попробуйте более чёткий снимок при хорошем освещении.");
      } else {
        setOcrText(text);
      }
    } catch {
      setOcrError(
        "Распознавание не удалось (проверьте подключение к интернету — модель загружается из сети). Можно впечатать текст вручную."
      );
    } finally {
      setOcrBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const insertOcrText = () => {
    setEssayText((prev) => (prev ? `${prev.trimEnd()}\n${ocrText}` : ocrText));
    setOcrText("");
    setOcrPreviewUrl(null);
  };

  const discardOcrText = () => {
    setOcrText("");
    setOcrPreviewUrl(null);
  };

  const verdict = essayType === "final" ? finalVerdict(checklist) : null;

  return (
    <div className="grid lg:grid-cols-[1fr_320px] gap-4">
      <div className="space-y-4">
        <Card>
          <label className="text-xs font-medium text-slate-500 mb-1 block">{cfg.sourceLabel}</label>
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            rows={essayType === "final" ? 2 : 6}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent text-sm"
            placeholder={cfg.sourcePlaceholder}
          />
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-medium text-slate-500">Ваше сочинение</label>
            <span className={`text-xs ${belowMin ? "text-amber-500" : "text-slate-400"}`}>
              {wordCount} слов {belowMin && `(минимум ${cfg.minWords})`}
            </span>
          </div>
          <textarea
            value={essayText}
            onChange={(e) => setEssayText(e.target.value)}
            rows={16}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent text-sm leading-relaxed"
            placeholder={cfg.essayPlaceholder}
          />
          <p className="text-xs text-slate-400 mt-1">
            Рекомендуемый объём — {cfg.recommendedWords} слов.
          </p>

          <div className="border-t border-slate-200 dark:border-slate-800 mt-3 pt-3 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={ocrBusy}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                📷 Загрузить фото сочинения
              </button>
              <span className="text-xs text-slate-400">
                Распознаёт печатный и аккуратный рукописный текст — результат нужно проверить и исправить.
              </span>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handlePhoto}
              />
            </div>

            {ocrBusy && (
              <div className="text-xs text-slate-500">
                Распознавание текста… {ocrProgress}%
                <div className="w-full h-1.5 rounded bg-slate-200 dark:bg-slate-700 mt-1 overflow-hidden">
                  <div
                    className="h-full bg-indigo-600 transition-all"
                    style={{ width: `${ocrProgress}%` }}
                  />
                </div>
              </div>
            )}

            {ocrError && <p className="text-xs text-rose-500">{ocrError}</p>}

            {ocrPreviewUrl && !ocrBusy && ocrText && (
              <div className="space-y-2">
                <div className="flex gap-3">
                  <img
                    src={ocrPreviewUrl}
                    alt="Загруженное фото сочинения"
                    className="w-20 h-20 object-cover rounded-lg border border-slate-200 dark:border-slate-700"
                  />
                  <div className="flex-1">
                    <p className="text-xs text-slate-500 mb-1">Распознанный текст (проверьте перед вставкой):</p>
                    <textarea
                      value={ocrText}
                      onChange={(e) => setOcrText(e.target.value)}
                      rows={4}
                      className="w-full px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent text-xs"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={insertOcrText}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700"
                  >
                    Вставить в сочинение
                  </button>
                  <button
                    type="button"
                    onClick={discardOcrText}
                    className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    Отменить
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between mt-3">
            <button
              onClick={save}
              disabled={saving || !essayText.trim()}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? "Сохранение…" : "Сохранить черновик"}
            </button>
            {savedAt && (
              <span className="text-xs text-slate-400">Сохранено в {savedAt.toLocaleTimeString()}</span>
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
              <label key={c.code} className="flex items-start gap-2 text-sm cursor-pointer">
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
            {criteria.length === 0 && <p className="text-sm text-slate-400">Загрузка критериев…</p>}
          </div>
          {verdict && (
            <div
              className={`mt-3 text-sm font-medium px-3 py-2 rounded-lg ${
                verdict.pass
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                  : "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
              }`}
            >
              {verdict.label}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
