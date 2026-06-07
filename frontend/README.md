# DKH Abnahme-App – React/PWA Basis

Diese Version überführt den bisherigen HTML-Prototyp in eine saubere React/Vite-Struktur. Sie ist als Basis für PWA, Android/iOS-Verpackung per Capacitor und Windows/macOS-Verpackung per Tauri gedacht.

## Enthalten

- React + Vite App-Struktur
- DKH-Design aus dem bestehenden Verwaltungsportal
- Mobile-first / Tablet-optimiertes Layout
- PWA Manifest und Service Worker
- Vorgangsverwaltung mit lokaler Browser-Speicherung
- Räume, Mängel mit Foto, Zähler mit Foto, Schlüssel
- Unterschriften per Touch/Maus
- Protokollansicht mit Browser-Druck/PDF

## Lokal starten

```bash
npm install
npm run dev
```

Danach im Browser öffnen:

```text
http://localhost:5173
```

## Build für Server app.dkh.immo

```bash
npm run build
```

Der Inhalt des Ordners `dist/` wird auf den Webserver kopiert.

Beispiel mit Nginx:

```nginx
server {
    server_name app.dkh.immo;
    root /var/www/app.dkh.immo;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Nächste technische Schritte

1. Backend/API ergänzen
2. Login und Benutzerrollen ergänzen
3. Datenbank und Dateispeicher einbinden
4. PDF serverseitig erzeugen
5. Tauri für Windows/macOS hinzufügen
6. Capacitor für Android/iOS hinzufügen
