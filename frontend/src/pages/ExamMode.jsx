import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import Card from "../components/Card.jsx";

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

export default function ExamMode() {
  const [params] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [variant, setVariant] = useState(null);
  const [answers, setAnswers] = useState({});
  const [secondsLeft, setSecondsLeft] = useState(null);
  const [finished, setFinished] = useState(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    api.subjects().then((res) => setSubjects(res.results ?? res));
  }, []);

  useEffect(() => {
    if (secondsLeft === null) return;
    if (secondsLeft <= 0) {
      finish();
      return;
    }
    timerRef.current = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft]);

  const start = async (subjectId) => {
    setStarting(true);
    setError(null);
    try {
      const v = await api.createExamVariant(subjectId);
      setVariant(v);
      setSecondsLeft(v.time_limit_minutes * 60);
      setFinished(null);
      setAnswers({});
    } catch (e) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  };

  const finish = async () => {
    clearTimeout(timerRef.current);
    const entries = Object.entries(answers).filter(([, v]) => v && v.trim());
    await Promise.all(
      entries.map(([taskId, value]) =>
        api.submitAttempt(Number(taskId), value.trim(), "exam", variant.id)
      )
    );
    const result = await api.finishExamVariant(variant.id);
    setFinished(result);
    setSecondsLeft(null);
  };

  if (!variant) {
    const preselected = params.get("subject");
    return (
      <div className="space-y-4 max-w-xl">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Вариант на время</h1>
        <p className="text-slate-500 text-sm">
          Соберётся один случайный вариант из заданий по всем темам выбранного предмета, с ограничением по
          времени — как на настоящем экзамене.
        </p>
        {error && <Card className="border-rose-300 text-rose-600">{error}</Card>}
        <div className="flex gap-3 flex-wrap">
          {subjects.map((s) => (
            <button
              key={s.id}
              disabled={starting}
              onClick={() => start(s.id)}
              className="px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-950 text-left disabled:opacity-50"
              autoFocus={preselected === String(s.id)}
            >
              <div className="font-medium">{s.name}</div>
              <div className="text-xs text-slate-500">Начать вариант</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (finished) {
    return (
      <Card className="max-w-xl">
        <h2 className="text-lg font-semibold mb-2">Вариант завершён</h2>
        <p className="text-slate-600 dark:text-slate-300">
          Правильных ответов: <b>{finished.score}</b> из <b>{finished.tasks.length}</b>
        </p>
        <button
          onClick={() => setVariant(null)}
          className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          Начать новый вариант
        </button>
      </Card>
    );
  }

  const answeredCount = Object.values(answers).filter((v) => v && v.trim()).length;

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between sticky top-16 bg-slate-50/90 dark:bg-slate-900/90 backdrop-blur py-2 z-10">
        <span className="text-sm text-slate-500">
          Отвечено {answeredCount} из {variant.tasks.length}
        </span>
        <span
          className={`font-mono text-lg font-semibold px-3 py-1 rounded-lg ${
            secondsLeft < 60 ? "text-rose-600" : "text-slate-900 dark:text-white"
          }`}
        >
          ⏱ {formatTime(secondsLeft ?? 0)}
        </span>
      </div>

      {variant.tasks.map((task, i) => (
        <Card key={task.id}>
          <div className="text-xs text-slate-400 mb-1">Задание {i + 1}</div>
          <p className="whitespace-pre-line mb-3 text-slate-800 dark:text-slate-200">{task.text}</p>
          {task.task_type === "choice" && task.options ? (
            <div className="flex flex-col gap-2">
              {task.options.map((opt) => (
                <label key={opt} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name={`task-${task.id}`}
                    checked={answers[task.id] === opt}
                    onChange={() => setAnswers((a) => ({ ...a, [task.id]: opt }))}
                  />
                  {opt}
                </label>
              ))}
            </div>
          ) : (
            <input
              value={answers[task.id] || ""}
              onChange={(e) => setAnswers((a) => ({ ...a, [task.id]: e.target.value }))}
              placeholder="Ваш ответ"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent"
            />
          )}
        </Card>
      ))}

      <button
        onClick={finish}
        className="w-full px-4 py-3 rounded-xl bg-indigo-600 text-white font-medium hover:bg-indigo-700"
      >
        Завершить вариант
      </button>
    </div>
  );
}
