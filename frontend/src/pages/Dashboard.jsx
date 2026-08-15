import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Card from "../components/Card.jsx";
import AccuracyBar from "../components/AccuracyBar.jsx";

export default function Dashboard() {
  const [subjects, setSubjects] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.subjects(), api.stats()])
      .then(([subjectsRes, statsRes]) => {
        setSubjects(subjectsRes.results ?? subjectsRes);
        setStats(statsRes);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <Card className="border-rose-300 text-rose-600">
        Не удалось загрузить данные: {error}. Проверьте, что бэкенд запущен и доступен по VITE_API_URL.
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Привет! 👋</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Тренируйся по темам, реши вариант на время или потренируй сочинение — прогресс сохраняется автоматически.
        </p>
      </div>

      {stats && (
        <Card>
          <h2 className="font-medium mb-3">Общий прогресс</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-semibold text-slate-900 dark:text-white">
                {stats.overall.attempts}
              </div>
              <div className="text-xs text-slate-500">попыток решено</div>
            </div>
            <div>
              <div className="text-2xl font-semibold text-slate-900 dark:text-white">
                {stats.overall.accuracy ?? "—"}
                {stats.overall.accuracy !== null && "%"}
              </div>
              <div className="text-xs text-slate-500">точность</div>
            </div>
            <div>
              <div className="text-2xl font-semibold text-slate-900 dark:text-white">
                {stats.exam_variants_completed}
              </div>
              <div className="text-xs text-slate-500">вариантов пройдено</div>
            </div>
          </div>
        </Card>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        {subjects.map((subject) => (
          <Card key={subject.id}>
            <h2 className="font-medium text-lg mb-2">{subject.name}</h2>
            <div className="flex gap-2 flex-wrap">
              <Link
                to={`/topics?subject=${subject.slug}`}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
              >
                Тренироваться по темам
              </Link>
              <Link
                to={`/exam?subject=${subject.id}`}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Вариант на время
              </Link>
            </div>
          </Card>
        ))}
        {subjects.length === 0 && (
          <Card>
            Пока нет предметов. Выполните на бэкенде <code>python manage.py seed_demo</code>.
          </Card>
        )}
      </div>

      {stats && stats.weak_topics.length > 0 && (
        <Card>
          <h2 className="font-medium mb-3">Слабые темы</h2>
          <div className="space-y-3">
            {stats.weak_topics.map((t) => (
              <div key={t.topic_id}>
                <div className="flex justify-between text-sm mb-1">
                  <Link to={`/practice/${t.topic_id}`} className="hover:underline">
                    №{t.task_number} {t.title}
                  </Link>
                </div>
                <AccuracyBar accuracy={t.accuracy} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
