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
    ["lÃ¶schen", "löschen"],
    ["LÃ¶schen", "Löschen"],
    ["VorgÃ¤nge", "Vorgänge"],
    ["VorgÃ¤ngen", "Vorgängen"],
    ["AuffÃ¤llig", "Auffällig"],
    ["GeprÃ¼ft", "Geprüft"],
    ["ZÃ¤hler", "Zähler"],
    ["MÃ¤ngel", "Mängel"],
    ["MÃ¤ngeln", "Mängeln"],
    ["Ãœbergabe", "Übergabe"],
    ["Ã¼bergabe", "übergabe"],
    ["Ãœbergaben", "Übergaben"],
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

// Funktionen für Speichern und Navigation vor return einfügen
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
  };`
  );
}

// Sidebar-Navigation komplett ersetzen
main = main.replace(
  /<nav className="side-nav">[\s\S]*?<\/nav>/,
  `<nav className="side-nav">
          <button type="button" className={!activeId ? 'active' : ''} onClick={goDashboard}>Dashboard</button>
          <button type="button" className={activeId ? 'active' : ''} onClick={goAbnahmen}>Abnahmen</button>
          <button type="button" onClick={() => alert('Wohnungen werden in einer späteren Version ergänzt.')}>Wohnungen</button>
          <button type="button" onClick={() => { goAbnahmen(); setTab('zaehler'); }}>Zähler</button>
          <button type="button" onClick={() => active ? setShowProtocol(true) : alert('Bitte zuerst einen Vorgang auswählen.')}>Protokolle</button>
        </nav>`
);

// Action-Leiste ersetzen, damit Speichern sicher vorhanden ist
main = main.replace(
  /<div className="actions">[\s\S]*?<button className="primary" onClick=\{\(\) => patchActive\(\{ status: 'Abgeschlossen' \}\)\}>[\s\S]*?<\/button>\s*<\/div>/,
  `<div className="actions">
                  <button className="danger" onClick={removeActive}><Trash2 size={18} /> Löschen</button>
                  <button onClick={saveNow}><Save size={18} /> Speichern</button>
                  <button onClick={() => setShowProtocol(true)}><FileText size={18} /> Protokoll</button>
                  <button className="primary" onClick={() => patchActive({ status: 'Abgeschlossen' })}><Save size={18} /> Abschließen</button>
                </div>`
);

// CSS für echte Sidebar-Buttons
css += `

/* Finale Sidebar-Navigation als echte Buttons */
.side-nav a {
  display: none !important;
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

/* Action-Buttons lesbarer */
.actions {
  gap: 10px;
  flex-wrap: wrap;
}
`;

fs.writeFileSync(mainPath, main, "utf8");
fs.writeFileSync(cssPath, css, "utf8");

console.log("Patch erfolgreich: Dashboard-Navigation, Speichern-Button und Umlaute wurden repariert.");
