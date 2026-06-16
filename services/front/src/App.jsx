import { useEffect, useState } from "react";
import { listNotes, searchNotes, createNote, deleteNote } from "./api.js";

export default function App() {
  const [notes, setNotes] = useState([]);
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh(q) {
    try {
      setError(null);
      const data = q ? await searchNotes(q) : await listNotes();
      setNotes(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleSearchSubmit(e) {
    e.preventDefault();
    await refresh(query);
  }

  async function handleCreateSubmit(e) {
    e.preventDefault();
    try {
      setError(null);
      await createNote(title, content);
      setTitle("");
      setContent("");
      await refresh(query);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleDelete(id) {
    try {
      setError(null);
      await deleteNote(id);
      await refresh(query);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="app">
      <h1>Mes notes</h1>

      {error && <div className="error-banner">{error}</div>}

      <form className="search-bar" onSubmit={handleSearchSubmit}>
        <input
          placeholder="Rechercher une note par titre..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit">Rechercher</button>
        {query && (
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setQuery("");
              refresh("");
            }}
          >
            Réinitialiser
          </button>
        )}
      </form>

      <form className="note-form" onSubmit={handleCreateSubmit}>
        <input
          placeholder="Titre"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="Contenu"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
        />
        <button type="submit">Créer la note</button>
      </form>

      {loading ? (
        <p>Chargement...</p>
      ) : notes.length === 0 ? (
        <p className="empty-state">Aucune note pour le moment.</p>
      ) : (
        <div className="notes-list">
          {notes.map((note) => (
            <div className="note-card" key={note.id}>
              <h3>{note.title}</h3>
              <p>{note.content}</p>
              <div className="note-card-actions">
                <button className="secondary" onClick={() => handleDelete(note.id)}>
                  Supprimer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
