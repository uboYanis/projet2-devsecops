async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("Session expirée ou accès refusé. Rechargez la page pour vous reconnecter.");
  }
  if (res.status === 429) {
    throw new Error("Trop de requêtes, merci de patienter avant de réessayer.");
  }
  if (res.status === 422) {
    const body = await res.json();
    throw new Error(body.detail?.[0]?.msg || "Données invalides.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erreur ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function getMe() {
  return request("/me");
}

export function listNotes() {
  return request("/notes");
}

export function searchNotes(q) {
  return request(`/notes/search?q=${encodeURIComponent(q)}`);
}

export function createNote(title, content) {
  return request("/notes", {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });
}

export function updateNote(id, title, content) {
  return request(`/notes/${id}`, {
    method: "PUT",
    body: JSON.stringify({ title, content }),
  });
}

export function deleteNote(id) {
  return request(`/notes/${id}`, { method: "DELETE" });
}
