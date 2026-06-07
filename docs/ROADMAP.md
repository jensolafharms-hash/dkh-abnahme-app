# Roadmap MVP 1 - DKH Abnahme-App

## Grundsatz

Zuerst lokal entwickeln und stabilisieren. Erst danach Staging/Produktion auf `app.dkh.immo`.

## Ticket 1 - Lokale Projektbasis stabilisieren

Status: umgesetzt in dieser Version.

- einheitliches Setup per `npm run setup`
- Frontend und Backend gemeinsam per `npm run dev`
- lokale `.env`-Dateien aus `.env.example`
- lokale Datenordner automatisch anlegen
- lokaler Uploadordner automatisch anlegen
- Reset-Skript fuer lokale Entwicklungsdaten
- README fuer lokalen Start

## Ticket 2 - Datenmodell finalisieren

- Benutzer
- Vorgang
- Objekt/Wohnung
- beteiligte Personen
- Raeume
- Maengel
- Fotos
- Zaehlerstaende
- Schluessel
- Unterschriften
- Protokolle

## Ticket 3 - Workflow und Statuslogik

- Entwurf
- In Bearbeitung
- Zur Unterschrift
- Abgeschlossen
- Archiviert
- schreibgeschuetzte abgeschlossene Vorgaenge

## Ticket 4 - Uploads und Fotos

- echte Uploads an Backend
- Zuordnung zu Raum, Mangel, Zaehler oder Unterschrift
- lokale Vorschau
- Komprimierung
- spaeter austauschbarer Speicherort

## Ticket 5 - PDF-Protokoll

- DKH-Layout
- Raumprotokoll
- Maengelliste
- Fotodokumentation
- Zaehlerstaende
- Schluessel
- Vereinbarungen
- Unterschriften

## Ticket 6 - Mobile/Tablet Optimierung

- Bedienung mit Touch
- Sticky Aktionsleiste
- bessere Kamera-Eingaben
- bessere Schritt-fuer-Schritt Fuehrung
- optimierte Protokollansicht
