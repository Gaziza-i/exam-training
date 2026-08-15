import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Topics from "./pages/Topics.jsx";
import Practice from "./pages/Practice.jsx";
import ExamMode from "./pages/ExamMode.jsx";
import Essay from "./pages/Essay.jsx";
import Stats from "./pages/Stats.jsx";

const navLinkClass = ({ isActive }) =>
  `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
    isActive
      ? "bg-indigo-600 text-white"
      : "text-slate-600 dark:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-slate-800"
  }`;

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-4 flex-wrap">
          <NavLink to="/" className="font-semibold text-lg text-slate-900 dark:text-white">
            🎓 Умный тренажёр ЕГЭ
          </NavLink>
          <nav className="flex gap-1 flex-wrap">
            <NavLink to="/" end className={navLinkClass}>Главная</NavLink>
            <NavLink to="/topics" className={navLinkClass}>Темы</NavLink>
            <NavLink to="/exam" className={navLinkClass}>Вариант на время</NavLink>
            <NavLink to="/essay" className={navLinkClass}>Сочинение</NavLink>
            <NavLink to="/stats" className={navLinkClass}>Статистика</NavLink>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/topics" element={<Topics />} />
          <Route path="/practice/:topicId" element={<Practice />} />
          <Route path="/exam" element={<ExamMode />} />
          <Route path="/essay" element={<Essay />} />
          <Route path="/stats" element={<Stats />} />
        </Routes>
      </main>

      <footer className="text-center text-xs text-slate-400 py-4">
        Задания из открытого банка ФИПИ · сделано для подготовки к ЕГЭ
      </footer>
    </div>
  );
}
