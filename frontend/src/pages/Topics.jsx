import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import Card from "../components/Card.jsx";
import AccuracyBar from "../components/AccuracyBar.jsx";

export default function Topics() {
  const [params, setParams] = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [statsByTopic, setStatsByTopic] = useState({});
  const [loading, setLoading] = useState(true);

  const subjectSlug = params.get("subject") || "rus";

  useEffect(() => {
    api.subjects().then((res) => setSubjects(res.results ?? res));
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.topics(subjectSlug), api.stats(subjectSlug)])
      .then(([topicsRes, statsRes]) => {
        setTopics(topicsRes.results ?? topicsRes);
        const map = {};
        for (const t of statsRes.topics) map[t.topic_id] = t;
        setStatsByTopic(map);
      })
      .finally(() => setLoading(false));
  }, [subjectSlug]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Темы</h1>
        <div className="flex gap-1">
          {subjects.map((s) => (
            <button
              key={s.id}
              onClick={() => setParams({ subject: s.slug })}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${
                subjectSlug === s.slug
                  ? "bg-indigo-600 border-indigo-600 text-white"
                  : "border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>
      </div>

      {loading && <Card>Загрузка…</Card>}

      <div className="grid gap-3">
        {topics.map((topic) => {
          const stat = statsByTopic[topic.id];
          const disabled = topic.task_count === 0;
          return (
            <Card key={topic.id} className={disabled ? "opacity-60" : ""}>
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="text-xs text-slate-400">Задание №{topic.task_number}</div>
                  <div className="font-medium text-slate-900 dark:text-white">{topic.title}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {topic.task_count} задани{topic.task_count === 1 ? "е" : "й"} в базе
                  </div>
                </div>
                <div className="flex items-center gap-4 w-full sm:w-64">
                  <AccuracyBar accuracy={stat?.accuracy ?? null} />
                </div>
                {disabled ? (
                  <span className="text-xs text-slate-400 px-3 py-1.5">нет заданий</span>
                ) : (
                  <Link
                    to={`/practice/${topic.id}`}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 shrink-0"
                  >
                    Тренироваться
                  </Link>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
