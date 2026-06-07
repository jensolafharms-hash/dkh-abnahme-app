import fs from "fs";
import path from "path";

const mainPath = path.resolve("frontend/src/main.jsx");
const cssPath = path.resolve("frontend/src/styles.css");

let main = fs.readFileSync(mainPath, "utf8");
let css = fs.readFileSync(cssPath, "utf8");

// Abmelden-Button gezielt mit Klasse versehen
main = main.replace(
  /<button([^>]*)>(\s*)Abmelden(\s*)<\/button>/g,
  `<button$1 className="logout-button">$2Abmelden$3</button>`
);

// Falls dadurch doppelte className entstehen sollte, bereinigen
main = main.replace(
  /<button([^>]*)className="([^"]*)"([^>]*) className="logout-button">/g,
  `<button$1className="$2 logout-button"$3>`
);

css += `

/* Final: Abmelden exakt wie Header-Hauptbutton dimensionieren */
.logout-button {
  min-height: 52px !important;
  height: 52px !important;
  padding: 0 30px !important;
  border-radius: 999px !important;
  font-size: 16px !important;
  font-weight: 800 !important;
  line-height: 1 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  white-space: nowrap !important;
  background: #ffffff !important;
  color: #09251C !important;
  border: 1px solid rgba(0, 63, 45, .16) !important;
  box-shadow: none !important;
}

/* Header-Aktionsbereich sauber ausrichten */
.top-actions,
.header-actions,
.app-header-actions,
.header-right {
  display: flex !important;
  align-items: center !important;
  gap: 16px !important;
}

/* Neuer Vorgang und Abmelden optisch gleich hoch */
.logout-button,
button.primary {
  min-height: 52px !important;
  height: 52px !important;
}
`;

fs.writeFileSync(mainPath, main, "utf8");
fs.writeFileSync(cssPath, css, "utf8");

console.log("Abmelden-Button wurde gezielt angepasst.");
