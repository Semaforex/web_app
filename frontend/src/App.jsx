import { useEffect, useMemo, useState } from 'react';
import './App.css';

function apiBase() {
  const raw = import.meta.env.VITE_BACKEND_URL;
  if (!raw) return '';
  return raw.endsWith('/') ? raw.slice(0, -1) : raw;
}

async function apiFetch(path, { token, ...init } = {}) {
  const headers = new Headers(init.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${apiBase()}${path}`, { ...init, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

function Login({ onLogin }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      });
      onLogin(data.token);
    } catch (err) {
      setError(err?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h2>Log in</h2>
        <p className="muted">Single-user app. Enter your password to continue.</p>
        <form onSubmit={submit} className="form">
          <label className="field">
            <div className="label">Password</div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoFocus
            />
          </label>
          {error ? <div className="error">{error}</div> : null}
          <button className="button" disabled={loading || !password.trim()}>
            {loading ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <p className="muted small">
          Backend: <code>{apiBase() || '(same origin)'}</code>
        </p>
      </div>
    </div>
  );
}

function Tabs({ tab, setTab }) {
  return (
    <div className="tabs">
      <button className={tab === 'tasks' ? 'tab active' : 'tab'} onClick={() => setTab('tasks')}>
        Tasks
      </button>
      <button className={tab === 'shop' ? 'tab active' : 'tab'} onClick={() => setTab('shop')}>
        Shop
      </button>
      <button
        className={tab === 'inventory' ? 'tab active' : 'tab'}
        onClick={() => setTab('inventory')}
      >
        Inventory
      </button>
    </div>
  );
}

function TasksTab({ token, points, onPoints }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [deadline, setDeadline] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [taskPoints, setTaskPoints] = useState('');
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/tasks', { token });
      setTasks(data.tasks || []);
    } catch (err) {
      setError(err?.message || 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createTask = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      const payload = {
        name,
        deadline: deadline || null,
        difficulty: difficulty || null,
        points: taskPoints === '' ? null : Number(taskPoints),
      };
      const data = await apiFetch('/api/tasks', {
        token,
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setTasks((prev) => [data.task, ...prev]);
      setName('');
      setDeadline('');
      setDifficulty('');
      setTaskPoints('');
    } catch (err) {
      setError(err?.message || 'Failed to create task');
    } finally {
      setCreating(false);
    }
  };

  const complete = async (id) => {
    setError('');
    try {
      const data = await apiFetch(`/api/tasks/${id}/complete`, { token, method: 'POST' });
      onPoints(data.points);
      setTasks((prev) => prev.map((t) => (t.id === id ? data.task : t)));
    } catch (err) {
      setError(err?.message || 'Failed to complete task');
    }
  };

  return (
    <div className="stack">
      <div className="card">
        <div className="row">
          <h2>Tasks</h2>
          <div className="pill">
            Points: <strong>{points}</strong>
          </div>
        </div>

        <form onSubmit={createTask} className="form">
          <div className="grid">
            <label className="field">
              <div className="label">Name *</div>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Do 30 min workout" />
            </label>
            <label className="field">
              <div className="label">Deadline (optional)</div>
              <input value={deadline} onChange={(e) => setDeadline(e.target.value)} placeholder="e.g. 2026-04-20" />
            </label>
            <label className="field">
              <div className="label">Difficulty (optional)</div>
              <input value={difficulty} onChange={(e) => setDifficulty(e.target.value)} placeholder="easy / medium / hard" />
            </label>
            <label className="field">
              <div className="label">Points (optional)</div>
              <input
                inputMode="numeric"
                value={taskPoints}
                onChange={(e) => setTaskPoints(e.target.value)}
                placeholder="e.g. 10"
              />
            </label>
          </div>
          {error ? <div className="error">{error}</div> : null}
          <div className="row">
            <button className="button" disabled={creating || !name.trim()}>
              {creating ? 'Adding…' : 'Add task'}
            </button>
            <button type="button" className="button secondary" onClick={load} disabled={loading}>
              Refresh
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        {loading ? <div className="muted">Loading…</div> : null}
        {!loading && tasks.length === 0 ? <div className="muted">No tasks yet. Add one above.</div> : null}
        <div className="list">
          {tasks.map((t) => (
            <div key={t.id} className={t.completed ? 'item done' : 'item'}>
              <div className="itemMain">
                <div className="itemTitle">{t.name}</div>
                <div className="itemMeta">
                  {t.deadline ? <span>Deadline: {t.deadline}</span> : null}
                  {t.difficulty ? <span>Difficulty: {t.difficulty}</span> : null}
                  <span>Points: {t.points ?? 0}</span>
                </div>
              </div>
              <div className="itemActions">
                {t.completed ? (
                  <span className="muted small">Completed</span>
                ) : (
                  <button className="button tiny" onClick={() => complete(t.id)}>
                    Mark completed
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ShopTab({ token, points, onPoints }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/shop', { token });
      setItems(data.items || []);
    } catch (err) {
      setError(err?.message || 'Failed to load shop');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buy = async (itemId) => {
    setError('');
    try {
      const data = await apiFetch('/api/shop/purchase', {
        token,
        method: 'POST',
        body: JSON.stringify({ itemId }),
      });
      onPoints(data.points);
    } catch (err) {
      setError(err?.message || 'Purchase failed');
    }
  };

  return (
    <div className="stack">
      <div className="card">
        <div className="row">
          <h2>Shop</h2>
          <div className="pill">
            Points: <strong>{points}</strong>
          </div>
        </div>
        <p className="muted">Buy items using points earned from completing tasks.</p>
        {error ? <div className="error">{error}</div> : null}
        <div className="list">
          {loading ? <div className="muted">Loading…</div> : null}
          {!loading && items.length === 0 ? <div className="muted">No items.</div> : null}
          {items.map((it) => (
            <div key={it.id} className="item">
              <div className="itemMain">
                <div className="itemTitle">{it.name}</div>
                <div className="itemMeta">
                  <span>Cost: {it.cost}</span>
                </div>
              </div>
              <div className="itemActions">
                <button
                  className="button tiny"
                  onClick={() => buy(it.id)}
                  disabled={points < it.cost}
                  title={points < it.cost ? 'Not enough points' : 'Purchase'}
                >
                  Purchase
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="row">
          <button type="button" className="button secondary" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}

function InventoryTab() {
  return (
    <div className="card">
      <h2>Inventory</h2>
      <p className="muted">
        Placeholder for future work: purchased items will show up here, and you’ll be able to use them.
      </p>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '');
  const [tab, setTab] = useState('tasks');
  const [points, setPoints] = useState(0);
  const [bootError, setBootError] = useState('');

  const authed = useMemo(() => Boolean(token), [token]);

  const logout = () => {
    localStorage.removeItem('token');
    setToken('');
    setTab('tasks');
    setPoints(0);
  };

  const onLogin = (t) => {
    localStorage.setItem('token', t);
    setToken(t);
  };

  useEffect(() => {
    if (!authed) return;
    let cancelled = false;
    (async () => {
      setBootError('');
      try {
        const data = await apiFetch('/api/me', { token });
        if (!cancelled) setPoints(data.points ?? 0);
      } catch (err) {
        if (!cancelled) setBootError(err?.message || 'Failed to load profile');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authed, token]);

  if (!authed) return <Login onLogin={onLogin} />;

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">Tasks & Shop</div>
        <Tabs tab={tab} setTab={setTab} />
        <div className="spacer" />
        <div className="pill">
          Points: <strong>{points}</strong>
        </div>
        <button className="button secondary tiny" onClick={logout}>
          Log out
        </button>
      </header>

      {bootError ? <div className="error">{bootError}</div> : null}

      {tab === 'tasks' ? <TasksTab token={token} points={points} onPoints={setPoints} /> : null}
      {tab === 'shop' ? <ShopTab token={token} points={points} onPoints={setPoints} /> : null}
      {tab === 'inventory' ? <InventoryTab /> : null}
    </div>
  );
}

export default App;