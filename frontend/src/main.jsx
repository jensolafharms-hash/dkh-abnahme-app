import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ClipboardCheck, Home, KeyRound, Gauge, Camera, FileText, Plus, Save, Printer, Trash2, CheckCircle2, AlertTriangle, Clock3, Inbox } from 'lucide-react';
import './styles.css';

const STORAGE_KEY = 'dkhAbnahmeReactCasesV2';
const AUTH_KEY = 'dkhAbnahmeAuthV1';
const API_BASE = import.meta.env.VITE_API_BASE || '';
const DEFAULT_ROOMS = ['Wohnzimmer', 'Schlafzimmer', 'Küche', 'Bad', 'Flur', 'Balkon / Terrasse', 'Keller'];
const DEFAULT_KEYS = ['Haustür', 'Wohnungstür', 'Briefkasten', 'Keller'];
const CATEGORIES = ['Wand', 'Boden', 'Decke', 'Fenster', 'Tür', 'Sanitär', 'Elektro', 'Heizung', 'Küche', 'Reinigung', 'Sonstiges'];

function uid() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}

function emptyCase() {
  const now = new Date();
  return {
    id: uid(),
    number: `DKH-${now.getFullYear()}-${String(now.getTime()).slice(-5)}`,
    type: 'Wohnungsabnahme Auszug',
    status: 'Entwurf',
    address: '',
    unit: '',
    date: '',
    responsible: '',
    oldTenant: '',
    newTenant: '',
    notes: '',
    agreements: '',
    rooms: DEFAULT_ROOMS.map(name => ({ id: uid(), name, condition: 'nicht geprüft', notes: '' })),
    defects: [],
    meters: [],
    keys: DEFAULT_KEYS.map(type => ({ id: uid(), type, expected: 1, actual: 1, number: '', notes: '' })),
    signatures: { manager: '', tenant: '' },
    createdAt: now.toISOString(),
    updatedAt: now.toISOString()
  };
}

function readCases() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

async function fileToDataUrl(file, maxSize = 1400) {
  const imageUrl = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = imageUrl;
    });
    const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.78);
  } finally {
    URL.revokeObjectURL(imageUrl);
  }
}

function App() {
  const [auth, setAuth] = useState(() => {
    try { return JSON.parse(localStorage.getItem(AUTH_KEY) || 'null'); } catch { return null; }
  });
  const [loginError, setLoginError] = useState('');
  const [cases, setCases] = useState(() => readCases());
  const [activeId, setActiveId] = useState(() => readCases()[0]?.id || '');
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState('basis');
  const [showProtocol, setShowProtocol] = useState(false);
  const [syncState, setSyncState] = useState('lokal');
  const remoteLoaded = useRef(false);
  const syncTimer = useRef(null);

  const api = async (url, options = {}) => {
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(auth?.token ? { Authorization: `Bearer ${auth.token}` } : {}), ...(options.headers || {}) }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Serverfehler');
    return data;
  };

  const login = async (email, password) => {
    setLoginError('');
    try {
      const data = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      }).then(async response => {
        const json = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(json.error || 'Anmeldung fehlgeschlagen');
        return json;
      });
      const nextAuth = { token: data.token, user: data.user };
      localStorage.setItem(AUTH_KEY, JSON.stringify(nextAuth));
      setAuth(nextAuth);
    } catch (error) {
      setLoginError(error.message);
    }
  };

  const logout = async () => {
    try { if (auth?.token) await api('/api/auth/logout', { method: 'POST' }); } catch {}
    localStorage.removeItem(AUTH_KEY);
    setAuth(null);
    remoteLoaded.current = false;
  };

  useEffect(() => {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
  }, []);

  useEffect(() => {
    if (!auth?.token) return;
    let ignore = false;
    setSyncState('lade');
    api('/api/cases')
      .then(data => {
        if (ignore) return;
        const remoteCases = Array.isArray(data.cases) ? data.cases : [];
        setCases(remoteCases);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(remoteCases));
        setActiveId(remoteCases[0]?.id || '');
        remoteLoaded.current = true;
        setSyncState('synchronisiert');
      })
      .catch(() => {
        remoteLoaded.current = true;
        setSyncState('offline');
      });
    return () => { ignore = true; };
  }, [auth?.token]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cases));
    if (!auth?.token || !remoteLoaded.current) return;
    clearTimeout(syncTimer.current);
    syncTimer.current = setTimeout(() => {
      setSyncState('speichere');
      api('/api/cases', { method: 'PUT', body: JSON.stringify({ cases }) })
        .then(() => setSyncState('synchronisiert'))
        .catch(() => setSyncState('offline'));
    }, 600);
    return () => clearTimeout(syncTimer.current);
  }, [cases, auth?.token]);

  if (!auth?.token) return <LoginView onLogin={login} error={loginError} />;

  const active = cases.find(item => item.id === activeId);
  const filtered = cases.filter(item => [item.number, item.address, item.unit, item.oldTenant, item.newTenant, item.status].join(' ').toLowerCase().includes(query.toLowerCase()));
  const stats = {
    total: cases.length,
    open: cases.filter(item => item.status !== 'Abgeschlossen').length,
    defects: cases.filter(item => item.defects.length > 0).length,
    done: cases.filter(item => item.status === 'Abgeschlossen').length
  };

  const patchActive = patch => {
    setCases(prev => prev.map(item => item.id === activeId ? { ...item, ...patch, updatedAt: new Date().toISOString() } : item));
  };

  const updateCollection = (name, id, patch) => {
    if (!active) return;
    patchActive({ [name]: active[name].map(item => item.id === id ? { ...item, ...patch } : item) });
  };

  const addCase = () => {
    const c = emptyCase();
    setCases(prev => [c, ...prev]);
    setActiveId(c.id);
    setTab('basis');
  };

  const removeActive = () => {
    if (!active || !confirm('Diesen Vorgang wirklich löschen?')) return;
    const next = cases.filter(item => item.id !== active.id);
    setCases(next);
    setActiveId(next[0]?.id || '');
  };

  const saveNow = async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cases));

    if (!auth?.token || !remoteLoaded.current) {
      setSyncState('lokal');
      alert('Vorgang wurde lokal gespeichert.');
      return;
    }

    try {
      setSyncState('speichere');
      await api('/api/cases', { method: 'PUT', body: JSON.stringify({ cases }) });
      setSyncState('synchronisiert');
      alert('Vorgang wurde gespeichert.');
    } catch {
      setSyncState('offline');
      alert('Vorgang wurde lokal gespeichert. Der Server ist aktuell nicht erreichbar.');
    }
  };

  const goDashboard = () => {
    setActiveId('');
    setTab('basis');
    setShowProtocol(false);
  };

  const goAbnahmen = () => {
    if (!activeId && cases[0]) setActiveId(cases[0].id);
    setTab('basis');
    setShowProtocol(false);
  };

  return (
    <div className="app-shell">
      <aside className="brand-sidebar">
        <div className="brand-logo-wrap"><img src="/assets/dkh-logo.png?v=logo-richtig-20260607-1925" alt="DKH Immobilienverwaltung" /></div>
        <nav className="side-nav">
          <button type="button" className={!activeId ? 'active' : ''} onClick={goDashboard}>Dashboard</button>
          <button type="button" className={activeId ? 'active' : ''} onClick={goAbnahmen}>Abnahmen</button>
          <button type="button" onClick={() => alert('Wohnungen werden in einer späteren Version ergänzt.')}>Wohnungen</button>
          <button type="button" onClick={() => { goAbnahmen(); setTab('zaehler'); }}>Zähler</button>
          <button type="button" onClick={() => active ? setShowProtocol(true) : alert('Bitte zuerst einen Vorgang auswählen.')}>Protokolle</button>
        </nav>
        <div className="contact-card">
          <strong>DKH-Immobilienverwaltung</strong><br />
          Hauptstr. 31<br />42349 Wuppertal<br /><br />
          Tel. 0202 – 890 199 26<br />www.dkh.immo
        </div>
      </aside>

      <main className="content-shell">
        <header className="app-header">
          <div><p className="eyebrow">Abnahmeportal</p><h1>Wohnungsabnahme</h1></div>
          <div className="header-actions"><span>{syncStateLabel(syncState)} · Willkommen, {auth.user?.name || 'Admin'}</span><button onClick={logout}>Abmelden</button><button className="primary" onClick={addCase}><Plus size={18} /> Neuer Vorgang</button></div>
        </header>

        <section className="stats-grid" aria-label="Kennzahlen">
          <Stat icon={<Inbox />} label="Vorgänge" value={stats.total} hint="Gesamt" />
          <Stat icon={<Clock3 />} label="Offen" value={stats.open} hint="In Bearbeitung" />
          <Stat icon={<AlertTriangle />} label="Auffällig" value={stats.defects} hint="Mit Mängeln" />
          <Stat icon={<CheckCircle2 />} label="Geprüft" value={stats.done} hint="Abgeschlossen" />
        </section>

        <section className="workspace" id="vorgaenge">
          <aside className="case-panel card">
            <label className="search-label">Suche
              <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Suche Einheit, Mieter, Adresse" />
            </label>
            <div className="case-list">
              {filtered.length === 0 && <p className="muted">Keine Vorgänge gefunden.</p>}
              {filtered.map(item => (
                <button key={item.id} className={`case-item ${item.id === activeId ? 'active' : ''}`} onClick={() => setActiveId(item.id)}>
                  <strong>{item.address || 'Neue Wohnung'}</strong>
                  <span>{item.number} · {item.unit || 'ohne Einheit'}</span>
                  <em>{item.status}</em>
                </button>
              ))}
            </div>
          </aside>

          <section className="editor card">
            {!active ? <EmptyState onAdd={addCase} /> : (
              <>
                <div className="editor-head">
                  <div><p className="eyebrow small">{active.number}</p><h2>{active.address || 'Neuer Vorgang'}</h2></div>
                  <span className="badge">{active.status}</span>
                </div>
                <Tabs value={tab} onChange={setTab} />
                {tab === 'basis' && <Basis active={active} patch={patchActive} />}
                {tab === 'raeume' && <Rooms active={active} patch={patchActive} update={updateCollection} />}
                {tab === 'maengel' && <Defects active={active} patch={patchActive} update={updateCollection} />}
                {tab === 'zaehler' && <Meters active={active} patch={patchActive} update={updateCollection} />}
                {tab === 'schluessel' && <Keys active={active} patch={patchActive} update={updateCollection} />}
                {tab === 'unterschrift' && <Signatures active={active} patch={patchActive} />}
                <div className="actions">
                  <button className="danger" onClick={removeActive}><Trash2 size={18} /> Löschen</button>
                  <button onClick={saveNow}><Save size={18} /> Speichern</button>
                  <button onClick={() => setShowProtocol(true)}><FileText size={18} /> Protokoll</button>
                  <button className="primary" onClick={() => patchActive({ status: 'Abgeschlossen' })}><Save size={18} /> Abschließen</button>
                </div>
              </>
            )}
          </section>
        </section>
      </main>

      {showProtocol && active && <ProtocolDialog item={active} onClose={() => setShowProtocol(false)} />}
    </div>
  );
}

function syncStateLabel(state) {
  return ({ lade: 'Lade Serverdaten', speichere: 'Speichere', synchronisiert: 'Synchronisiert', offline: 'Offline/Lokal', lokal: 'Lokal' })[state] || state;
}

function LoginView({ onLogin, error }) {
  const [email, setEmail] = useState('admin@dkh.immo');
  const [password, setPassword] = useState('Admin123!');
  const [busy, setBusy] = useState(false);
  const submit = async event => {
    event.preventDefault();
    setBusy(true);
    await onLogin(email, password);
    setBusy(false);
  };
  return <div className="login-screen">
    <form className="login-card" onSubmit={submit}>
      <img src="/assets/dkh-logo.png?v=logo-richtig-20260607-1925" alt="DKH Immobilienverwaltung" />
      <p className="eyebrow">Abnahmeportal</p>
      <h1>Anmeldung</h1>
      <label>E-Mail<input value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" /></label>
      <label>Passwort<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></label>
      {error && <p className="error-box">{error}</p>}
      <button className="primary" disabled={busy}>{busy ? 'Bitte warten ...' : 'Anmelden'}</button>
      <small>Standardzugang für lokale Tests: admin@dkh.immo / Admin123! Bitte auf dem Server ändern.</small>
    </form>
  </div>;
}

function Stat({ icon, label, value, hint }) {
  return <article className="stat-card"><span className="stat-icon">{icon}</span><div><span>{label}</span><strong>{value}</strong><small>{hint}</small></div></article>;
}

function Tabs({ value, onChange }) {
  const tabs = [['basis', 'Basisdaten', Home], ['raeume', 'Räume', ClipboardCheck], ['maengel', 'Mängel', Camera], ['zaehler', 'Zähler', Gauge], ['schluessel', 'Schlüssel', KeyRound], ['unterschrift', 'Unterschrift', FileText]];
  return <div className="tabs">{tabs.map(([id, label, Icon]) => <button key={id} className={value === id ? 'active' : ''} onClick={() => onChange(id)}><Icon size={17} /> {label}</button>)}</div>;
}

function EmptyState({ onAdd }) {
  return <div className="empty-state"><h2>Noch kein Vorgang ausgewählt</h2><p>Lege eine neue Wohnungsabnahme oder Übergabe an.</p><button className="primary" onClick={onAdd}><Plus size={18} /> Vorgang anlegen</button></div>;
}

function Basis({ active, patch }) {
  const bind = field => ({ value: active[field] || '', onChange: event => patch({ [field]: event.target.value }) });
  return <div className="panel-grid">
    <label>Vorgangstyp<select {...bind('type')}><option>Wohnungsabnahme Auszug</option><option>Wohnungsübergabe Einzug</option><option>Zwischenabnahme</option><option>Sonstige Begehung</option></select></label>
    <label>Status<select {...bind('status')}><option>Entwurf</option><option>Geplant</option><option>In Bearbeitung</option><option>Abgeschlossen</option></select></label>
    <label>Objektadresse<input {...bind('address')} placeholder="Straße, PLZ Ort" /></label>
    <label>Wohnung / Einheit<input {...bind('unit')} placeholder="z. B. WE-204" /></label>
    <label>Termin<input type="datetime-local" {...bind('date')} /></label>
    <label>Verantwortlich<input {...bind('responsible')} placeholder="Name" /></label>
    <label>Bisheriger Mieter<input {...bind('oldTenant')} /></label>
    <label>Neuer Mieter<input {...bind('newTenant')} /></label>
    <label className="full">Notizen<textarea rows="3" {...bind('notes')} /></label>
    <label className="full">Besondere Vereinbarungen<textarea rows="3" {...bind('agreements')} /></label>
  </div>;
}

function Rooms({ active, patch, update }) {
  const add = () => patch({ rooms: [...active.rooms, { id: uid(), name: '', condition: 'nicht geprüft', notes: '' }] });
  const remove = id => patch({ rooms: active.rooms.filter(item => item.id !== id) });
  return <Collection title="Räume" onAdd={add} addLabel="Raum hinzufügen">
    {active.rooms.map(room => <ItemCard key={room.id} title={room.name || 'Raum'} onRemove={() => remove(room.id)}>
      <div className="panel-grid compact">
        <label>Raum<input value={room.name} onChange={e => update('rooms', room.id, { name: e.target.value })} /></label>
        <label>Zustand<select value={room.condition} onChange={e => update('rooms', room.id, { condition: e.target.value })}><option>nicht geprüft</option><option>in Ordnung</option><option>mit Mängeln</option></select></label>
        <label className="full">Bemerkung<textarea rows="2" value={room.notes || ''} onChange={e => update('rooms', room.id, { notes: e.target.value })} /></label>
      </div>
    </ItemCard>)}
  </Collection>;
}

function Defects({ active, patch, update }) {
  const add = () => patch({ defects: [...active.defects, { id: uid(), room: active.rooms[0]?.name || '', category: 'Wand', severity: 'gering', responsibility: 'offen', description: '', photo: '' }] });
  const remove = id => patch({ defects: active.defects.filter(item => item.id !== id) });
  const onPhoto = async (id, file) => update('defects', id, { photo: await fileToDataUrl(file) });
  return <Collection title="Mängel" onAdd={add} addLabel="Mangel hinzufügen">
    {active.defects.map(defect => <ItemCard key={defect.id} title={defect.category || 'Mangel'} onRemove={() => remove(defect.id)}>
      <div className="panel-grid compact">
        <label>Raum<select value={defect.room} onChange={e => update('defects', defect.id, { room: e.target.value })}>{active.rooms.map(room => <option key={room.id}>{room.name}</option>)}</select></label>
        <label>Kategorie<select value={defect.category} onChange={e => update('defects', defect.id, { category: e.target.value })}>{CATEGORIES.map(v => <option key={v}>{v}</option>)}</select></label>
        <label>Schweregrad<select value={defect.severity} onChange={e => update('defects', defect.id, { severity: e.target.value })}><option>gering</option><option>mittel</option><option>erheblich</option></select></label>
        <label>Verantwortlichkeit<select value={defect.responsibility} onChange={e => update('defects', defect.id, { responsibility: e.target.value })}><option>offen</option><option>Mieter</option><option>Vermieter</option><option>Verwaltung</option></select></label>
        <label className="full">Beschreibung<textarea rows="3" value={defect.description || ''} onChange={e => update('defects', defect.id, { description: e.target.value })} /></label>
        <PhotoInput photo={defect.photo} onPhoto={file => onPhoto(defect.id, file)} />
      </div>
    </ItemCard>)}
  </Collection>;
}

function Meters({ active, patch, update }) {
  const add = () => patch({ meters: [...active.meters, { id: uid(), type: 'Strom', number: '', reading: '', unit: 'kWh', notes: '', photo: '' }] });
  const remove = id => patch({ meters: active.meters.filter(item => item.id !== id) });
  const onPhoto = async (id, file) => update('meters', id, { photo: await fileToDataUrl(file) });
  return <Collection title="Zählerstände" onAdd={add} addLabel="Zähler hinzufügen">
    {active.meters.map(meter => <ItemCard key={meter.id} title={meter.type} onRemove={() => remove(meter.id)}>
      <div className="panel-grid compact">
        <label>Typ<select value={meter.type} onChange={e => update('meters', meter.id, { type: e.target.value })}><option>Strom</option><option>Wasser kalt</option><option>Wasser warm</option><option>Heizung</option><option>Gas</option><option>Sonstige</option></select></label>
        <label>Zählernummer<input value={meter.number || ''} onChange={e => update('meters', meter.id, { number: e.target.value })} /></label>
        <label>Zählerstand<input value={meter.reading || ''} onChange={e => update('meters', meter.id, { reading: e.target.value })} /></label>
        <label>Einheit<input value={meter.unit || ''} onChange={e => update('meters', meter.id, { unit: e.target.value })} /></label>
        <label className="full">Bemerkung<textarea rows="2" value={meter.notes || ''} onChange={e => update('meters', meter.id, { notes: e.target.value })} /></label>
        <PhotoInput photo={meter.photo} onPhoto={file => onPhoto(meter.id, file)} />
      </div>
    </ItemCard>)}
  </Collection>;
}

function Keys({ active, patch, update }) {
  const add = () => patch({ keys: [...active.keys, { id: uid(), type: '', expected: 1, actual: 1, number: '', notes: '' }] });
  const remove = id => patch({ keys: active.keys.filter(item => item.id !== id) });
  return <Collection title="Schlüsselübergabe" onAdd={add} addLabel="Schlüssel hinzufügen">
    {active.keys.map(key => <ItemCard key={key.id} title={key.type || 'Schlüssel'} onRemove={() => remove(key.id)}>
      <div className="panel-grid compact">
        <label>Schlüsselart<input value={key.type || ''} onChange={e => update('keys', key.id, { type: e.target.value })} /></label>
        <label>Schlüsselnummer<input value={key.number || ''} onChange={e => update('keys', key.id, { number: e.target.value })} /></label>
        <label>Soll-Anzahl<input type="number" value={key.expected || 0} onChange={e => update('keys', key.id, { expected: e.target.value })} /></label>
        <label>Ist-Anzahl<input type="number" value={key.actual || 0} onChange={e => update('keys', key.id, { actual: e.target.value })} /></label>
        <label className="full">Bemerkung<textarea rows="2" value={key.notes || ''} onChange={e => update('keys', key.id, { notes: e.target.value })} /></label>
      </div>
    </ItemCard>)}
  </Collection>;
}

function Signatures({ active, patch }) {
  return <div className="signature-grid">
    <SignaturePad title="Verwaltung / DKH" value={active.signatures.manager} onChange={manager => patch({ signatures: { ...active.signatures, manager } })} />
    <SignaturePad title="Mieter / Vertragspartner" value={active.signatures.tenant} onChange={tenant => patch({ signatures: { ...active.signatures, tenant } })} />
  </div>;
}

function SignaturePad({ title, value, onChange }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#064326';
    if (value) {
      const img = new Image();
      img.onload = () => ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      img.src = value;
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, [value]);

  const point = event => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const source = event.touches?.[0] || event;
    return { x: (source.clientX - rect.left) * (canvas.width / rect.width), y: (source.clientY - rect.top) * (canvas.height / rect.height) };
  };
  const start = event => { event.preventDefault(); const ctx = canvasRef.current.getContext('2d'); const p = point(event); drawing.current = true; ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = event => { if (!drawing.current) return; event.preventDefault(); const ctx = canvasRef.current.getContext('2d'); const p = point(event); ctx.lineTo(p.x, p.y); ctx.stroke(); };
  const end = () => { if (!drawing.current) return; drawing.current = false; onChange(canvasRef.current.toDataURL('image/png')); };
  const clear = () => { const canvas = canvasRef.current; canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height); onChange(''); };

  return <div className="signature-card"><h3>{title}</h3><canvas ref={canvasRef} width="900" height="260" onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end} onTouchStart={start} onTouchMove={move} onTouchEnd={end} /><button onClick={clear}>Unterschrift löschen</button></div>;
}

function Collection({ title, onAdd, addLabel, children }) {
  return <section><div className="section-header"><h3>{title}</h3><button className="secondary" onClick={onAdd}><Plus size={17} /> {addLabel}</button></div><div className="stack">{children}</div></section>;
}

function ItemCard({ title, onRemove, children }) {
  return <article className="item-card"><div className="item-head"><strong>{title}</strong><button className="danger" onClick={onRemove}><Trash2 size={16} /> Entfernen</button></div>{children}</article>;
}

function PhotoInput({ photo, onPhoto }) {
  return <label className="photo-input full">Foto<input type="file" accept="image/*" capture="environment" onChange={e => e.target.files?.[0] && onPhoto(e.target.files[0])} />{photo && <img src={photo} alt="Dokumentation" />}</label>;
}

function ProtocolDialog({ item, onClose }) {
  return <div className="dialog-backdrop" role="dialog" aria-modal="true">
    <div className="dialog">
      <div className="dialog-header"><h2>Übergabeprotokoll</h2><div><button onClick={() => window.print()}><Printer size={17} /> Drucken / PDF</button><button onClick={onClose}>Schließen</button></div></div>
      <Protocol item={item} />
    </div>
  </div>;
}

function Protocol({ item }) {
  return <article className="protocol" id="print-protocol">
    <header><img src="/assets/dkh-logo.png?v=logo-richtig-20260607-1925" alt="DKH" /><div><h1>Wohnungsabnahme / Übergabe</h1><p>{item.number} · {item.type} · Status: {item.status}</p></div></header>
    <Info title="Basisdaten" rows={[["Adresse", item.address], ["Einheit", item.unit], ["Termin", item.date], ["Verantwortlich", item.responsible], ["Bisheriger Mieter", item.oldTenant], ["Neuer Mieter", item.newTenant], ["Notizen", item.notes], ["Vereinbarungen", item.agreements]]} />
    <Info title="Räume" rows={item.rooms.map(r => [r.name, `${r.condition}${r.notes ? ' – ' + r.notes : ''}`])} />
    <Info title="Mängel" rows={item.defects.map(d => [d.room || d.category, `${d.category}, ${d.severity}, ${d.responsibility}: ${d.description || ''}`])} />
    <PhotoStrip items={item.defects} title="Mängelfotos" />
    <Info title="Zählerstände" rows={item.meters.map(m => [m.type, `${m.number || '-'} · ${m.reading || '-'} ${m.unit || ''} ${m.notes ? '· ' + m.notes : ''}`])} />
    <PhotoStrip items={item.meters} title="Zählerfotos" />
    <Info title="Schlüssel" rows={item.keys.map(k => [k.type, `Soll: ${k.expected}, Ist: ${k.actual}${k.number ? ', Nr. ' + k.number : ''}${k.notes ? ' – ' + k.notes : ''}`])} />
    <section><h2>Unterschriften</h2><div className="protocol-signatures">{item.signatures.manager && <img src={item.signatures.manager} alt="Unterschrift Verwaltung" />}{item.signatures.tenant && <img src={item.signatures.tenant} alt="Unterschrift Mieter" />}</div></section>
  </article>;
}

function Info({ title, rows }) {
  return <section><h2>{title}</h2><table><tbody>{rows.length ? rows.map(([key, value], index) => <tr key={index}><th>{key}</th><td>{value || '-'}</td></tr>) : <tr><td>Keine Angaben</td></tr>}</tbody></table></section>;
}

function PhotoStrip({ items, title }) {
  const photos = items.filter(item => item.photo);
  if (!photos.length) return null;
  return <section><h2>{title}</h2><div className="photo-strip">{photos.map(item => <img key={item.id} src={item.photo} alt={title} />)}</div></section>;
}

createRoot(document.getElementById('root')).render(<App />);

