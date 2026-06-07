# DKH Abnahme-App - lokale Entwicklungsbasis

Diese Version ist bewusst auf **lokale Entwicklung zuerst** ausgelegt. Der Server `app.dkh.immo` ist erst spaeter das Deployment-Ziel. Lokal koennen Frontend, Backend, Daten und Uploads ohne Risiko weiterentwickelt und getestet werden.

## Inhalt

- `frontend/` - React + Vite + PWA im DKH-Design
- `backend/` - Node.js/Express API mit Login, Vorgangspeicherung und Upload-Vorbereitung
- `backend/data/` - lokale Entwicklungsdaten, wird automatisch angelegt
- `backend/uploads/` - lokale Uploads, wird automatisch angelegt
- `scripts/` - Setup- und Reset-Skripte fuer die lokale Entwicklung
- `docs/` - Roadmap und Entwicklungsnotizen

## Voraussetzungen

- Node.js 20 LTS oder neuer empfohlen
- npm

Pruefen:

```bash
node -v
npm -v
```

## Schnellstart lokal

Im Projektordner:

```bash
npm install
npm run install:all
npm run dev
```

Danach im Browser oeffnen:

```text
http://localhost:5173
```

Backend API:

```text
http://localhost:3100/api/health
```

## Demo-Login

```text
admin@dkh.immo
Admin123!
```

Das Passwort kann lokal in `backend/.env` geaendert werden. Wenn bereits eine lokale `backend/data/users.json` existiert, vorher `npm run reset:local` ausfuehren oder die Datei loeschen, damit der Admin neu erzeugt wird.

## Wichtige lokale Befehle

```bash
npm run setup
```

Legt lokale `.env`-Dateien, Datenordner und Uploadordner an.

```bash
npm run dev
```

Startet Backend und Frontend parallel im Entwicklungsmodus.

```bash
npm run build
npm start
```

Baut das Frontend und startet danach das Backend, das die gebaute App ausliefert.

```bash
npm run reset:local
```

Loescht lokale Entwicklungsdaten und Uploads. Danach werden sie beim naechsten Start neu angelegt.

## Lokale Datenhaltung

Aktuell speichert der MVP die Vorgangsdaten lokal im Backend unter:

```text
backend/data/cases.json
backend/data/users.json
```

Uploads werden lokal abgelegt unter:

```text
backend/uploads/
```

Das ist fuer die lokale MVP-Entwicklung absichtlich einfach gehalten. Fuer die produktionsnahe Version wird die Speicherung spaeter auf eine echte Datenbank wie PostgreSQL oder MySQL umgestellt.

## Entwicklung getrennt starten

Backend:

```bash
cd backend
npm install
npm run dev
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Build fuer spaeteres Deployment

```bash
npm run build
npm start
```

Wenn das lokal stabil laeuft, wird daraus spaeter ein Deployment fuer `app.dkh.immo` vorbereitet.

## Naechste Tickets

1. Datenmodell fachlich finalisieren
2. Vorgangsworkflow mit Statuslogik ausbauen
3. Foto-Uploads vom Base64-Prototyp auf echte Server-Uploads umstellen
4. PDF-Protokoll serverseitig erzeugen
5. Tablet- und Smartphone-UI weiter optimieren
6. spaeter Staging/Produktion auf `app.dkh.immo`
