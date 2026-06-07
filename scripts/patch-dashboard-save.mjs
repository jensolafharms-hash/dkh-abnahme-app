import fs from "fs";
import path from "path";

const mainPath = path.resolve("frontend/src/main.jsx");
const cssPath = path.resolve("frontend/src/styles.css");

let main = fs.readFileSync(mainPath, "utf8");
let css = fs.readFileSync(cssPath, "utf8");

// 1) saveNow-Funktion nach removeActive ergänzen
if (!main.includes("const saveNow = async () =>")) {
  main = main.replace(
`  const removeActive = () => {
    if (!active || !confirm('Diesen Vorgang wirklich löschen?')) return;
    const next = cases.filter(item => item.id !== active.id);
    setCases(next);
    setActiveId(next[0]?.id || '');
  };

  return (`,
`  const removeActive = () => {
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

  return (`
  );
}

// 2) Sidebar-Links durch echte Buttons ersetzen
main = main.replace(
`        <nav className="side-nav">
          <a className="active" href="#dashboard">Dashboard</a>
          <a href="#vorgaenge">Abnahmen</a>
          <a href="#wohnungen">Wohnungen</a>
          <a href="#zaehler">Zähler</a>
          <a href="#protokolle">Protokolle</a>
        </nav>`,
`        <nav className="side-nav">
          <button type="button" className={!activeId ? 'active' : ''} onClick={goDashboard}>Dashboard</button>
          <button type="button" className={activeId ? 'active' : ''} onClick={goAbnahmen}>Abnahmen</button>
          <button type="button" onClick={() => alert('Wohnungen werden in einer späteren Version ergänzt.')}>Wohnungen</button>
          <button type="button" onClick={() => { goAbnahmen(); setTab('zaehler'); }}>Zähler</button>
          <button type="button" onClick={() => active ? setShowProtocol(true) : alert('Bitte zuerst einen Vorgang auswählen.')}>Protokolle</button>
        </nav>`
);

// 3) Speichern-Button in Actions ergänzen
if (!main.includes("Speichern</button>")) {
  main = main.replace(
`                <div className="actions">
                  <button className="danger" onClick={removeActive}><Trash2 size={18} /> Löschen</button>
                  <button onClick={() => setShowProtocol(true)}><FileText size={18} /> Protokoll</button>
                  <button className="primary" onClick={() => patchActive({ status: 'Abgeschlossen' })}><Save size={18} /> Abschließen</button>
                </div>`,
`                <div className="actions">
                  <button className="danger" onClick={removeActive}><Trash2 size={18} /> Löschen</button>
                  <button onClick={saveNow}><Save size={18} /> Speichern</button>
                  <button onClick={() => setShowProtocol(true)}><FileText size={18} /> Protokoll</button>
                  <button className="primary" onClick={() => patchActive({ status: 'Abgeschlossen' })}><Save size={18} /> Abschließen</button>
                </div>`
  );
}

// 4) CSS für Sidebar-Buttons ergänzen
if (!css.includes("/* Sidebar echte Buttons */")) {
  css += `

/* Sidebar echte Buttons */
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
`;
}

fs.writeFileSync(mainPath, main, "utf8");
fs.writeFileSync(cssPath, css, "utf8");

console.log("Patch fertig: Speichern-Button und Dashboard-Navigation wurden ergänzt.");
