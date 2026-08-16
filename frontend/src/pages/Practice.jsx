import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, formatAnswer } from "../api.js";
import Card from "../components/Card.jsx";

export default function Practice() {
  const { topicId } = useParams();
  const [tasks, setTasks] = useState([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionStats, setSessionStats] = useState({ correct: 0, total: 0 });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setLoading(true);
    api
      .tasks({ topic: topicId })
      .then((res) => setTasks(res.results ?? res))
      .finally(() => setLoading(false));
  }, [topicId]);

  const task = tasks[index];

  const submit = async (e) => {
    e.preventDefault();
    if (!task || !answer.trim()) return;
    const res = await api.submitAttempt(task.id, answer.trim(), "practice");
    setResult(res);
    setSessionStats((s) => ({
      correct: s.correct + (res.is_correct ? 1 : 0),
      total: s.total + 1,
    }));
    setHistory((h) => [
      ...h,
      {
        task,
        userAnswer: answer.trim(),
        isCorrect: res.is_correct,
        correctAnswer: res.correct_answer,
        explanation: res.explanation,
      },
    ]);
  };

  const next = () => {
    setResult(null);
    setAnswer("");
    setIndex((i) => i + 1);
  };

  if (loading) return <Card>Загрузка…</Card>;

  if (!task) {
    return (
      <div className="space-y-4 max-w-2xl">
        <Card>
          <p className="mb-3">
            {tasks.length === 0
              ? "Для этой темы пока нет заданий в базе."
              : `Задания закончились. Правильных ответов: ${sessionStats.correct} из ${sessionStats.total}.`}
          </p>
          <Link to="/topics" className="text-indigo-600 hover:underline text-sm">
            ← Вернуться к темам
          </Link>
        </Card>

        {history.length > 0 && (
          <>
            <h3 className="font-medium text-slate-700 dark:text-slate-200">Разбор заданий</h3>
            {history.map((h, i) => (
              <Card key={i}>
                <div className="text-xs text-slate-400 mb-1">Задание {i + 1}</div>
                <p className="whitespace-pre-line mb-3 text-slate-800 dark:text-slate-200">{h.task.text}</p>
                <div
                  className={`inline-block px-3 py-1.5 rounded-lg text-sm font-medium ${
                    h.isCorrect
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                      : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"
                  }`}
                >
                  {h.isCorrect
                    ? "Верно ✅"
                    : `Неверно. Ваш ответ: «${h.userAnswer}». Правильный ответ: ${formatAnswer(h.correctAnswer)}`}
                </div>
                {h.explanation && <p className="text-sm text-slate-500 mt-2">{h.explanation}</p>}
              </Card>
            ))}
          </>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between text-sm text-slate-500">
        <Link to="/topics" className="hover:underline">← Темы</Link>
        <span>
          Задание {index + 1} из {tasks.length} · верно {sessionStats.correct}/{sessionStats.total}
        </span>
      </div>

      <Card>
        {task.source === "seed" && (
          <span className="inline-block mb-2 text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
            демо-задание
          </span>
        )}
        <p className="whitespace-pre-line text-slate-800 dark:text-slate-200">{task.text}</p>

        {!result ? (
          <form onSubmit={submit} className="mt-4 space-y-3">
            {task.task_type === "choice" && task.options ? (
              <div className="flex flex-col gap-2">
                {task.options.map((opt) => (
                  <label
                    key={opt}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer ${
                      answer === opt
                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950"
                        : "border-slate-300 dark:border-slate-700"
                    }`}
                  >
                    <input
                      type="radio"
                      name="answer"
                      value={opt}
                      checked={answer === opt}
                      onChange={(e) => setAnswer(e.target.value)}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            ) : (
              <input
                autoFocus
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Ваш ответ"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent"
              />
            )}
            <button
              type="submit"
              disabled={!answer.trim()}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              Проверить
            </button>
          </form>
        ) : (
          <div className="mt-4 space-y-3">
            <div
              className={`px-3 py-2 rounded-lg text-sm font-medium ${
                result.is_correct
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                  : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"
              }`}
            >
              {result.is_correct ? "Верно! ✅" : `Неверно. Правильный ответ: ${formatAnswer(result.correct_answer)}`}
            </div>
            {result.explanation && (
              <p className="text-sm text-slate-500">{result.explanation}</p>
            )}
            <button
              onClick={next}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
            >
              Следующее задание →
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
