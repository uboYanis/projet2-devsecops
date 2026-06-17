import { useCallback, useEffect, useRef, useState } from "react";
import { listNotes, searchNotes, createNote, updateNote, deleteNote, getMe } from "./api.js";
import { useDebounce } from "./useDebounce.js";
import { ToastStack } from "./Toasts.jsx";

const TITLE_MAX = 200;
const CONTENT_MAX = 10000;
const SEARCH_MAX = 100;

let toastSeq = 0;

export default function App() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);

  const [userEmail, setUserEmail] = useState(null);

  useEffect(() => {
    getMe()
      .then((me) => setUserEmail(me.email))
      .catch(() => setUserEmail(null));
  }, []);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const confirmTimeoutRef = useRef(null);

  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editSaving, setEditSaving] = useState(false);

  const [toasts, setToasts] = useState([]);

  const pushToast = useCallback((message, type = "error") => {
    const id = ++toastSeq;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const dismissToast = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const refresh = useCallback(async (q) => {
    try {
      const data = q ? await searchNotes(q) : await listNotes();
      setNotes(data);
    } catch (e) {
      pushToast(e.message);
    } finally {
      setLoading(false);
    }
  }, [pushToast]);

  useEffect(() => {
    if (debouncedQuery.length > SEARCH_MAX) return;
    refresh(debouncedQuery);
  }, [debouncedQuery, refresh]);

  async function handleCreateSubmit(e) {
    e.preventDefault();
    if (!title.trim() || !content.trim() || submitting) return;
    setSubmitting(true);
    try {
      await createNote(title.trim(), content.trim());
      setTitle("");
      setContent("");
      pushToast("Note créée", "success");
      await refresh(debouncedQuery);
    } catch (e) {
      pushToast(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleFormKeyDown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      handleCreateSubmit(e);
    }
  }

  function handleDeleteClick(id) {
    if (confirmDeleteId === id) {
      clearTimeout(confirmTimeoutRef.current);
      setConfirmDeleteId(null);
      doDelete(id);
      return;
    }
    setConfirmDeleteId(id);
    clearTimeout(confirmTimeoutRef.current);
    confirmTimeoutRef.current = setTimeout(() => setConfirmDeleteId(null), 3000);
  }

  async function doDelete(id) {
    const previous = notes;
    setNotes((prev) => prev.filter((n) => n.id !== id));
    try {
      await deleteNote(id);
      pushToast("Note supprimée", "success");
    } catch (e) {
      setNotes(previous);
      pushToast(e.message);
    }
  }

  function handleEditClick(note) {
    setConfirmDeleteId(null);
    setEditingId(note.id);
    setEditTitle(note.title);
    setEditContent(note.content);
  }

  function handleEditCancel() {
    setEditingId(null);
  }

  async function handleEditSave(id) {
    if (!editTitle.trim() || !editContent.trim() || editSaving) return;
    setEditSaving(true);
    try {
      await updateNote(id, editTitle.trim(), editContent.trim());
      pushToast("Note modifiée", "success");
      setEditingId(null);
      await refresh(debouncedQuery);
    } catch (e) {
      pushToast(e.message);
    } finally {
      setEditSaving(false);
    }
  }

  const searchTooLong = query.length > SEARCH_MAX;

  return (
    <div className="app">
      <ToastStack toasts={toasts} onDismiss={dismissToast} />

      <header className="app-header">
        <div className="app-header-text">
          <h1>Notes</h1>
          {!loading && <span className="count-badge">{notes.length}</span>}
        </div>
        <div className="app-header-actions">
          {userEmail ? (
            <div className="auth-pill">
              <span className="auth-email" title={userEmail}>{userEmail}</span>
              <a className="auth-link" href="/_gcp_iap/clear_login_cookie">Déconnexion</a>
            </div>
          ) : (
            <button type="button" className="secondary" onClick={() => window.location.reload()}>
              Se connecter
            </button>
          )}
        </div>
      </header>

      <form className="note-form" onSubmit={handleCreateSubmit} onKeyDown={handleFormKeyDown}>
        <input
          placeholder="Titre de la note"
          value={title}
          maxLength={TITLE_MAX}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          placeholder="Écrivez quelque chose... (Ctrl+Entrée pour valider)"
          value={content}
          maxLength={CONTENT_MAX}
          onChange={(e) => setContent(e.target.value)}
        />
        <div className="note-form-footer">
          <span className="char-counter">{title.length}/{TITLE_MAX}</span>
          <button type="submit" disabled={!title.trim() || !content.trim() || submitting}>
            {submitting ? "Création..." : "Créer la note"}
          </button>
        </div>
      </form>

      <div className="search-bar">
        <svg className="search-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          placeholder="Rechercher par titre..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Rechercher une note"
        />
        {query && (
          <button type="button" className="icon-btn" onClick={() => setQuery("")} aria-label="Effacer la recherche">
            ×
          </button>
        )}
      </div>
      {searchTooLong && (
        <p className="field-hint field-hint-error">Requête trop longue ({query.length}/{SEARCH_MAX})</p>
      )}
      {query && !searchTooLong && !loading && (
        <p className="field-hint">{notes.length} résultat{notes.length === 1 ? "" : "s"} pour « {query} »</p>
      )}

      {loading ? (
        <div className="notes-list">
          {[0, 1, 2].map((i) => (
            <div className="note-card skeleton" key={i}>
              <div className="skeleton-line skeleton-line-title" />
              <div className="skeleton-line" />
              <div className="skeleton-line skeleton-line-short" />
            </div>
          ))}
        </div>
      ) : notes.length === 0 ? (
        <div className="empty-state">
          <p>{query ? "Aucune note ne correspond à votre recherche." : "Aucune note pour le moment."}</p>
          {!query && <p className="empty-state-hint">Créez votre première note ci-dessus.</p>}
        </div>
      ) : (
        <div className="notes-list">
          {notes.map((note) =>
            editingId === note.id ? (
              <div className="note-card note-card-editing" key={note.id}>
                <input
                  value={editTitle}
                  maxLength={TITLE_MAX}
                  onChange={(e) => setEditTitle(e.target.value)}
                  autoFocus
                />
                <textarea
                  value={editContent}
                  maxLength={CONTENT_MAX}
                  onChange={(e) => setEditContent(e.target.value)}
                />
                <div className="note-card-actions">
                  <button className="secondary" onClick={handleEditCancel}>Annuler</button>
                  <button
                    onClick={() => handleEditSave(note.id)}
                    disabled={!editTitle.trim() || !editContent.trim() || editSaving}
                  >
                    {editSaving ? "Enregistrement..." : "Enregistrer"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="note-card" key={note.id}>
                <h3>{note.title}</h3>
                <p>{note.content}</p>
                <div className="note-card-actions">
                  <button className="secondary" onClick={() => handleEditClick(note)}>Modifier</button>
                  <button
                    className={confirmDeleteId === note.id ? "danger" : "secondary"}
                    onClick={() => handleDeleteClick(note.id)}
                  >
                    {confirmDeleteId === note.id ? "Confirmer ?" : "Supprimer"}
                  </button>
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
