const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  subjects: () => request("/subjects/"),
  topics: (subjectSlug) => request(`/topics/?subject=${subjectSlug}`),
  tasks: ({ subject, topic, random } = {}) => {
    const params = new URLSearchParams();
    if (subject) params.set("subject", subject);
    if (topic) params.set("topic", topic);
    if (random) params.set("random", random);
    return request(`/tasks/?${params.toString()}`);
  },
  submitAttempt: (taskId, userAnswer, mode = "practice", examVariant = null) =>
    request("/attempts/", {
      method: "POST",
      body: JSON.stringify({
        task: taskId,
        user_answer: userAnswer,
        mode,
        exam_variant: examVariant,
      }),
    }),
  createExamVariant: (subjectId) =>
    request("/exam-variants/", {
      method: "POST",
      body: JSON.stringify({ subject: subjectId }),
    }),
  finishExamVariant: (id) => request(`/exam-variants/${id}/finish/`, { method: "POST" }),
  getExamVariant: (id) => request(`/exam-variants/${id}/`),
  stats: (subjectSlug) => request(`/stats/${subjectSlug ? `?subject=${subjectSlug}` : ""}`),
  essayCriteria: () => request("/essay-criteria/"),
  essays: () => request("/essays/"),
  createEssay: (data) =>
    request("/essays/", { method: "POST", body: JSON.stringify(data) }),
  updateEssay: (id, data) =>
    request(`/essays/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
};
