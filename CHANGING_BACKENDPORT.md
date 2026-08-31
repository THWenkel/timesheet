# CHANGING_BACKENDPORT.md — Backend-Port wechseln

Dieses Dokument beschreibt alle notwendigen Schritte, um den Backend-Port von `8000`
auf einen neuen Port (Beispiel: `9000`) zu ändern.

---

## ToDo-Liste

### 1. Backend starten (uvicorn CLI)

- [ ] Uvicorn-Startbefehl anpassen:
      `uvicorn app.main:app --reload --host 0.0.0.0 --port <NEUER_PORT>`
  - Der Port wird ausschließlich per CLI-Argument übergeben.
  - Kein Code in `backend/app/main.py` muss geändert werden.

---

### 2. Frontend — Vite Dev-Server Proxy (`frontend/vite.config.ts`)

- [ ] `VITE_API_URL` in `frontend/.env` (oder `frontend/.env.local`) setzen:
      `VITE_API_URL=http://localhost:<NEUER_PORT>`
  - **Alternativ** (ohne .env-Datei): Den Fallback-Wert direkt in `vite.config.ts`
    Zeile 19 ändern:
    `const apiUrl = env.VITE_API_URL || "http://localhost:<NEUER_PORT>";`
  - Die `.env`-Variante ist bevorzugt, da kein Code geändert werden muss.

---

### 3. Frontend — API-Typen generieren (`frontend/package.json`)

- [ ] Das `generate-api`-Script in `package.json` (Zeile 17) anpassen:
      `"generate-api": "openapi-typescript http://localhost:<NEUER_PORT>/openapi.json -o src/api/generated.ts"`
  - Der Port ist hier **hartcodiert** und muss manuell geändert werden.
  - **Alternativ**: Script auf eine Umgebungsvariable umstellen, z. B.:
    `"generate-api": "openapi-typescript ${VITE_API_URL:-http://localhost:8000}/openapi.json -o src/api/generated.ts"`
    (nur unter Unix/macOS; unter Windows separates `.env`-Handling nötig)

---

### 4. API-Typen neu generieren

- [ ] Nach dem Portändern und während das Backend auf dem **neuen Port** läuft:
      `cd frontend && npm run generate-api`

---

### 5. Dokumentation aktualisieren

- [ ] `AGENTS.md` — alle Port-Referenzen aktualisieren (Zeilen 132, 135, 137, 139, 141, 208, 221)
- [ ] `backend/app/main.py` — Kommentar in Zeile 11 anpassen
- [ ] Diese Datei (`CHANGING_BACKENDPORT.md`) ggf. mit dem neuen Zielport aktualisieren

---

## Betroffene Dateien (Übersicht)

| Datei                        | Zeile | Typ                  | Aktion                        |
|------------------------------|-------|----------------------|-------------------------------|
| `frontend/vite.config.ts`    | 19    | Runtime-Fallback     | `.env`-Variable setzen        |
| `frontend/package.json`      | 17    | npm-Script           | Port im Script anpassen       |
| `backend/app/main.py`        | 11    | Kommentar            | Kommentar aktualisieren       |
| `AGENTS.md`                  | multi | Dokumentation        | Alle Referenzen aktualisieren |

---

## Hinweise

- `frontend/src/api/client.ts` enthält **keinen** hartcodierten Port — der API-Client
  nutzt `VITE_API_URL` bzw. verlässt sich auf den Vite-Proxy. Keine Änderung nötig.
- Die `.env`-Datei im Frontend-Verzeichnis ist **git-ignoriert**.
  Bei Teamarbeit muss jedes Teammitglied seine lokale `.env` anpassen.
- Der Backend-Port hat **keine** `.env`-Unterstützung out-of-the-box.
  Soll er konfigurierbar sein, müsste in `backend/app/core/config.py` ein
  `APP_PORT`-Setting ergänzt und in einem Start-Script ausgelesen werden.
