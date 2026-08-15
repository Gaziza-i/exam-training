import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Card from "../components/Card.jsx";
import AccuracyBar from "../components/AccuracyBar.jsx";

export default function Stats() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.stats().then(setStats);
  }, []);

  if (!stats) return <Card>Загрузка…</Card>;

  const attempted = stats.topics.filter((t) => t.attempts > 0);
  const notAttempted = stats.topics.filter((t) => t.attempts === 0);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Статистика</h1>

      <div className="grid sm:grid-cols-3 gap-4">
        <Card>
          <div className="text-2xl font-semibold">{stats.overall.attempts}</div>
          <div className="text-xs text-slate-500">решено заданий</div>
        </Card>
        <Card>
          <div className="text-2xl font-semibold">
            {stats.overall.accuracy ?? "—"}
            {stats.overall.accuracy !== null && "%"}
          </div>
          <div className="text-xs text-slate-500">общая точность</div>
        </Card>
        <Card>
          <div className="text-2xl font-semibold">{stats.exam_variants_completed}</div>
          <div className="text-xs text-slate-500">вариантов пройдено</div>
        </Card>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <Card>
          <h2 className="font-medium mb-3 text-rose-600">Слабые темы</h2>
          {stats.weak_topics.length === 0 && (
            <p className="text-sm text-slate-400">Пока нет попыток — начните тренировку.</p>
          )}
          <div className="space-y-3">
            {stats.weak_topics.map((t) => (
              <TopicRow key={t.topic_id} t={t} />
            ))}
          </div>
        </Card>
        <Card>
          <h2 className="font-medium mb-3 text-emerald-600">Сильные темы</h2>
          {stats.strong_topics.length === 0 && (
            <p className="text-sm text-slate-400">Пока нет попыток — начните тренировку.</p>
          )}
          <div className="space-y-3">
            {stats.strong_topics.map((t) => (
              <TopicRow key={t.topic_id} t={t} />
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="font-medium mb-3">Все темы</h2>
        <div className="space-y-3">
          {[...attempted, ...notAttempted].map((t) => (
            <TopicRow key={t.topic_id} t={t} />
          ))}
        </div>
      </Card>
    </div>
  );
}

function TopicRow({ t }) {
  return (
    <div className="flex items-center gap-4">
      <Link to={`/practice/${t.topic_id}`} className="flex-1 min-w-0 text-sm hover:underline truncate">
        №{t.task_number} {t.title}
      </Link>
      <div className="w-40 shrink-0">
        <AccuracyBar accuracy={t.accuracy} />
      </div>
    </div>
  );
}
