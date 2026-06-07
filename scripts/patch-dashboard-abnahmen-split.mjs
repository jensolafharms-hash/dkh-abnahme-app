import fs from "fs";
import path from "path";

const mainPath = path.resolve("frontend/src/main.jsx");
const cssPath = path.resolve("frontend/src/styles.css");

let main = fs.readFileSync(mainPath, "utf8");
let css = fs.readFileSync(cssPath, "utf8");

function fixText(content) {
  const fixes = [
    ["StraÃŸe", "Straße"],
    ["AbschlieÃŸen", "Abschließen"],
    ["SchlieÃŸen", "Schließen"],
    ["LÃ¶schen", "Löschen"],
    ["VorgÃ¤nge", "Vorgänge"],
    ["AuffÃ¤llig", "Auffällig"],
    ["GeprÃ¼ft", "Geprüft"],
    ["ZÃ¤hler", "Zähler"],
    ["MÃ¤ngel", "Mängel"],
    ["MÃ¤ngeln", "Mängeln"],
    ["Ãœbergabe", "Übergabe"],
    ["Ã¼bergabe", "übergabe"],
    ["ausgewÃ¤hlt", "ausgewählt"],
    ["Ã¤", "ä"],
    ["Ã¶", "ö"],
    ["Ã¼", "ü"],
    ["Ã„", "Ä"],
    ["Ã–", "Ö"],
    ["Ãœ", "Ü"],
    ["ÃŸ", "ß"],
    ["Â·", "·"],
    ["Â ", " "],
    ["â€“", "–"]
  ];

  for (const [bad, good] of fixes) {
    content = content.split(bad).join(good);
  }

  return content;
}

main = fixText(main);
css = fixText(css);

// View-State ergänzen
if (!main.includes("const [view, setView] = useState('dashboard');")) {
  main = main.replace(
    "const [showProtocol, setShowProtocol] = useState(false);",
    "const [showProtocol, setShowProtocol] = useState(false);\n  const [view, setView] = useState('dashboard');"
  );
}

// addCase soll immer in Abnahmen wechseln
main = main.replace(
  /const addCase = \(\) => \{\s*const c = emptyCase\(\);\s*setCases\(prev => \[c, \.\.\.prev\]\);\s*setActiveId\(c\.id\);\s*setTab\('basis'\);\s*\};/,
  `const addCase = () => {
    const c = emptyCase();
    setCases(prev => [c, ...prev]);
    setActiveId(c.id);
    setTab('basis');
    setShowProtocol(false);
    setView('abnahmen');
  };`
);

// Navigation-Funktionen neu setzen/ergänzen
if (main.includes("const goDashboard = () =>")) {
  main = main.replace(
    /const goDashboard = \(\) => \{[\s\S]*?\n\s+\};/,
    `const goDashboard = () => {
    setActiveId('');
    setTab('basis');
    setShowProtocol(false);
    setView('dashboard');
  };`
  );
} else {
  main = main.replace(
    /(\s+const removeActive = \(\) => \{[\s\S]*?\n\s+\};)/,
    `$1

  const goDashboard = () => {
    setActiveId('');
    setTab('basis');
    setShowProtocol(false);
    setView('dashboard');
  };`
  );
}

if (main.includes("const goAbnahmen = () =>")) {
  main = main.replace(
    /const goAbnahmen = \(\) => \{[\s\S]*?\n\s+\};/,
    `const goAbnahmen = () => {
    if (!activeId && cases[0]) setActiveId(cases[0].id);
    setTab('basis');
    setShowProtocol(false);
    setView('abnahmen');
  };`
  );
} else {
  main = main.replace(
    /(\s+const goDashboard = \(\) => \{[\s\S]*?\n\s+\};)/,
    `$1

  const goAbnahmen = () => {
    if (!activeId && cases[0]) setActiveId(cases[0].id);
    setTab('basis');
    setShowProtocol(false);
    setView('abnahmen');
  };`
  );
}

// Sidebar komplett auf echte Navigation setzen
main = main.replace(
  /<nav className="side-nav">[\s\S]*?<\/nav>/,
  `<nav className="side-nav">
          <button type="button" className={view === 'dashboard' ? 'active' : ''} onClick={goDashboard}>Dashboard</button>
          <button type="button" className={view === 'abnahmen' ? 'active' : ''} onClick={goAbnahmen}>Abnahmen</button>
          <button type="button" onClick={() => alert('Wohnungen werden in einer späteren Version ergänzt.')}>Wohnungen</button>
          <button type="button" onClick={() => { setView('abnahmen'); goAbnahmen(); setTab('zaehler'); }}>Zähler</button>
          <button type="button" onClick={() => active ? setShowProtocol(true) : alert('Bitte zuerst einen Vorgang auswählen.')}>Protokolle</button>
        </nav>`
);

// Action-Leiste sicher mit Speichern setzen
main = main.replace(
  /<div className="actions">[\s\S]*?<\/div>/,
  `<div className="actions">
                  <button className="danger" onClick={removeActive}><Trash2 size={18} /> Löschen</button>
                  <button onClick={saveNow}><Save size={18} /> Speichern</button>
                  <button onClick={() => setShowProtocol(true)}><FileText size={18} /> Protokoll</button>
                  <button className="primary" onClick={() => patchActive({ status: 'Abgeschlossen' })}><Save size={18} /> Abschließen</button>
                </div>`
);

// Falls saveNow fehlt, ergänzen
if (!main.includes("const saveNow = async () =>")) {
  main = main.replace(
    /(\s+const removeActive = \(\) => \{[\s\S]*?\n\s+\};)/,
    `$1

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
  };`
  );
}

// Workspace durch View-Umschaltung ersetzen
const workspaceStart = main.indexOf('        <section className="workspace" id="vorgaenge">');
const workspaceEndMarker = '        </section>\n      </main>';
if (workspaceStart !== -1) {
  const workspaceEnd = main.indexOf(workspaceEndMarker, workspaceStart);
  if (workspaceEnd !== -1) {
    const oldWorkspace = main.slice(workspaceStart, workspaceEnd + '        </section>'.length);
    const newWorkspace = `        {view === 'dashboard' ? (
          <DashboardHome
            cases={cases}
            stats={stats}
            onAdd={addCase}
            onOpen={(id) => {
              setActiveId(id);
              setTab('basis');
              setShowProtocol(false);
              setView('abnahmen');
            }}
          />
        ) : (
          <section className="workspace" id="vorgaenge">
            <aside className="case-panel card">
              <label className="search-label">Suche
                <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Suche Einheit, Mieter, Adresse" />
              </label>
              <div className="case-list">
                {filtered.length === 0 && <p className="muted">Keine Vorgänge gefunden.</p>}
                {filtered.map(item => (
                  <button key={item.id} className={\`case-item \${item.id === activeId ? 'active' : ''}\`} onClick={() => setActiveId(item.id)}>
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
        )}`;
    main = main.replace(oldWorkspace, newWorkspace);
  }
}

// DashboardHome-Komponente ergänzen
if (!main.includes("function DashboardHome(")) {
  main = main.replace(
    "function Tabs({ value, onChange }) {",
    `function DashboardHome({ cases, stats, onAdd, onOpen }) {
  const latest = cases.slice(0, 5);

  return <section className="dashboard-home">
    <article className="card dashboard-welcome">
      <div>
        <p className="eyebrow small">Übersicht</p>
        <h2>Dashboard</h2>
        <p className="muted">Hier siehst du den aktuellen Stand der Wohnungsabnahmen und Übergaben.</p>
      </div>
      <button className="primary" onClick={onAdd}><Plus size={18} /> Neuen Vorgang anlegen</button>
    </article>

    <div className="dashboard-panels">
      <article className="card">
        <h3>Letzte Vorgänge</h3>
        {latest.length === 0 ? <p className="muted">Noch keine Vorgänge vorhanden.</p> : (
          <div className="dashboard-list">
            {latest.map(item => (
              <button key={item.id} onClick={() => onOpen(item.id)}>
                <strong>{item.address || 'Neue Wohnung'}</strong>
                <span>{item.number} · {item.unit || 'ohne Einheit'} · {item.status}</span>
              </button>
            ))}
          </div>
        )}
      </article>

      <article className="card">
        <h3>Schnellübersicht</h3>
        <p className="muted">Offene Vorgänge: <strong>{stats.open}</strong></p>
        <p className="muted">Vorgänge mit Mängeln: <strong>{stats.defects}</strong></p>
        <p className="muted">Abgeschlossen: <strong>{stats.done}</strong></p>
      </article>
    </div>
  </section>;
}

function Tabs({ value, onChange }) {`
  );
}

// CSS ergänzen
if (!css.includes("/* Dashboard/Abnahmen Seitentrennung */")) {
  css += `

/* Dashboard/Abnahmen Seitentrennung */
.dashboard-home {
  display: grid;
  gap: 24px;
}

.dashboard-welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 30px;
}

.dashboard-welcome h2 {
  margin: 0 0 8px;
  font-size: 34px;
}

.dashboard-panels {
  display: grid;
  grid-template-columns: 1.4fr .8fr;
  gap: 24px;
}

.dashboard-panels .card {
  padding: 26px;
}

.dashboard-panels h3 {
  margin-top: 0;
  font-size: 22px;
}

.dashboard-list {
  display: grid;
  gap: 12px;
}

.dashboard-list button {
  text-align: left;
  border: 1px solid rgba(0, 63, 45, .14);
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
}

.dashboard-list button:hover {
  background: #F4F9EE;
}

.dashboard-list strong,
.dashboard-list span {
  display: block;
}

.dashboard-list span {
  color: #6B7671;
  margin-top: 4px;
}

.side-nav button {
  appearance: none;
  border: 0;
  width: 100%;
  text-align: left;
  background: transparent;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  padding: 18px 22px;
  border-radius: 16px;
  cursor: pointer;
}

.side-nav button:hover {
  background: rgba(255, 255, 255, .10);
}

.side-nav button.active {
  background: rgba(255, 255, 255, .14);
}

@media (max-width: 900px) {
  .dashboard-welcome {
    align-items: stretch;
    flex-direction: column;
  }

  .dashboard-panels {
    grid-template-columns: 1fr;
  }
}
`;
}

fs.writeFileSync(mainPath, main, "utf8");
fs.writeFileSync(cssPath, css, "utf8");

console.log("Dashboard und Abnahmen wurden getrennt.");
