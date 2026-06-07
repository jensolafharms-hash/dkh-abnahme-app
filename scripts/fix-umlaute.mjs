import fs from "fs";
import path from "path";

const files = [
  "frontend/src/main.jsx",
  "frontend/src/styles.css"
];

const replacements = [
  ["Vorg\u00c3\u00a4nge", "Vorgänge"],
  ["Vorg\u00c3\u00a4ngen", "Vorgängen"],
  ["Auff\u00c3\u00a4llig", "Auffällig"],
  ["Gepr\u00c3\u00bcft", "Geprüft"],
  ["Z\u00c3\u00a4hler", "Zähler"],
  ["M\u00c3\u00a4ngel", "Mängel"],
  ["M\u00c3\u00a4ngeln", "Mängeln"],
  ["\u00c3\u009cbergabe", "Übergabe"],
  ["\u00c3\u00bcbergabe", "übergabe"],
  ["\u00c3\u009cbergaben", "Übergaben"],
  ["ausgew\u00c3\u00a4hlt", "ausgewählt"],
  ["\u00c3\u00a4", "ä"],
  ["\u00c3\u00b6", "ö"],
  ["\u00c3\u00bc", "ü"],
  ["\u00c3\u0084", "Ä"],
  ["\u00c3\u0096", "Ö"],
  ["\u00c3\u009c", "Ü"],
  ["\u00c3\u009f", "ß"],
  ["\u00c2\u00b7", "·"],
  ["\u00c2\u00a0", " "],
  ["\u00e2\u20ac\u201c", "–"],
  ["\u00e2\u20ac\u0153", "“"],
  ["\u00e2\u20ac\u009d", "”"],
  ["\u00e2\u20ac\u2122", "’"],
  ["Offline/Lokal \u00c2\u00b7 Willkommen", "Offline/Lokal · Willkommen"],
  ["Tel. 0202 \u00e2\u20ac\u201c 890 199 26", "Tel. 0202 – 890 199 26"]
];

for (const file of files) {
  const fullPath = path.resolve(file);
  let content = fs.readFileSync(fullPath, "utf8");

  for (const [bad, good] of replacements) {
    content = content.split(bad).join(good);
  }

  fs.writeFileSync(fullPath, content, "utf8");
  console.log("Repariert:", fullPath);
}

console.log("UTF-8/Umlaute wurden repariert.");
