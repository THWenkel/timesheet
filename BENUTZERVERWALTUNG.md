# Benutzerverwaltung und Anmeldung

Diese Anleitung erklärt, wie Administratoren im Admin-Tool Benutzer anlegen, Passwörter vergeben und Rechte setzen, und wie sich Anwender anmelden. Die technischen Details stehen in [AGENTS.md](AGENTS.md) (Abschnitt „Authentifizierung (JWT)“).

## Kurzüberblick

- Es gibt **keine Selbstregistrierung** und **kein „Passwort vergessen“ per E-Mail**. Konten und erste Passwörter kommen immer von einem Administrator.
- Anmelden geht in der Web-App unter `/timesheet/login` mit **Benutzername** und **Passwort**.
- Ein Administrator vergibt ein **Einmalpasswort**. Der Anwender muss es bei der ersten Anmeldung durch ein eigenes ersetzen.
- Passwörter sind nirgends lesbar gespeichert, auch nicht für Administratoren.

## Die Benutzerliste im Admin-Tool

| Spalte | Bedeutung |
| --- | --- |
| **ID** | Interne Nummer des Mitarbeiters. |
| **Vorname / Nachname** | Name, wie er in Berichten und im Export erscheint. |
| **Benutzername** | Login-Name für die Anmeldung. Ohne Benutzername kann sich die Person nicht anmelden. |
| **Admin** | Die Person darf das Admin-Tool benutzen: Benutzer, Kunden und Projekte verwalten, Datensicherung und Wiederherstellung. Ohne Haken sieht und ändert der Benutzer in der Web-App nur die **eigenen** Zeiteinträge. |
| **Passwort** | Für das Konto ist ein Passwort gesetzt. Man sieht nur, dass eines existiert, nicht welches. Ohne Haken ist keine Anmeldung möglich. |
| **Aktiv** | Der Benutzer darf sich anmelden. Ein deaktivierter Benutzer ist sofort gesperrt, auch mitten in einer laufenden Sitzung. Seine Zeiteinträge bleiben erhalten. |
| **Geändert** | Zeitpunkt der letzten Änderung des Datensatzes. |

Damit sich jemand anmelden kann, müssen **Benutzername**, **Passwort** und **Aktiv** gesetzt sein.

Die Liste zeigt nicht, ob ein Einmalpasswort noch offen ist, die Person also ihr eigenes Passwort noch nicht gewählt hat. Das merkt man daran, dass die Web-App nach der Anmeldung sofort einen Passwortwechsel verlangt.

## Rollen

| | Normaler Benutzer | Administrator |
| --- | --- | --- |
| Web-App: eigene Zeiten erfassen, ansehen, exportieren | ja | ja |
| Zeiten anderer Mitarbeiter sehen, ändern, exportieren | nein | ja (Auswahl in der Web-App) |
| Admin-Tool starten (bei aktivem Login) | nein | ja |
| Benutzer, Kunden, Projekte verwalten | nein | ja |
| Datensicherung und Wiederherstellung | nein | ja |
| Einmalpasswörter setzen | nein | ja |

Das Adminrecht sollte nur bekommen, wer diese Aufgaben tatsächlich übernimmt.

## Aufgaben für Administratoren

### Neuen Benutzer anlegen

1. Admin-Tool → **Neu**: Vorname und Nachname eintragen.
2. Im Feld **Benutzername (Login)** einen Namen vergeben (mindestens 3 Zeichen, wird kleingeschrieben gespeichert, muss eindeutig sein).
3. **Administrator** nur ankreuzen, wenn die Person das Admin-Tool nutzen soll.
4. Speichern.
5. Den Benutzer markieren und **Einmalpasswort** klicken. Die Rückfrage mit **Ja** bestätigen.
6. Das Tool zeigt Benutzername und Einmalpasswort **einmalig** an und kopiert das Passwort in die Zwischenablage. Es wird danach nirgends mehr angezeigt.
7. Beides auf sicherem Weg weitergeben (persönlich oder telefonisch, nicht per unverschlüsselter Mail).

### Passwort zurücksetzen (z. B. „Passwort vergessen“)

Es gibt dafür keine Seite für Anwender. Der Administrator geht vor wie bei Schritt 5 bis 7 oben: Benutzer markieren → **Einmalpasswort** (auch per Rechtsklick → „Einmalpasswort setzen“).

Dabei passiert:

- Das alte Passwort wird ungültig.
- Alle laufenden Anmeldungen der Person werden beendet.
- Eine Sperre nach Fehlversuchen wird aufgehoben.
- Die Person muss bei der nächsten Anmeldung ein neues Passwort wählen.

### Benutzer sperren

Den Benutzer markieren und **Deaktivieren** klicken. Der Benutzer kann sich nicht mehr anmelden, eine laufende Sitzung endet sofort. Die Zeiteinträge bleiben erhalten. Wieder freigeben: **Bearbeiten** → Haken bei „Benutzer ist aktiv“.

Ein Administrator kann **sein eigenes Konto nicht deaktivieren** und sich **das eigene Adminrecht nicht entziehen**. Das Backend lehnt beides ab, damit sich niemand versehentlich aussperrt. Das macht bei Bedarf ein anderer Administrator.

### Zeiten anderer Mitarbeiter ansehen und ändern

Nur Administratoren sehen in der Web-App oben unter „Signed in as …“ zusätzlich die Auswahl **Employee**. Dort wählst du den Mitarbeiter, dessen Zeiten du sehen willst. Kalender, Tages- und Wochenansicht, Erfassen, Ändern und der Export arbeiten dann für diesen Mitarbeiter. Ein Hinweis „You are viewing and editing the timesheet of …“ zeigt, dass es nicht die eigenen Zeiten sind. Die Auswahl zeigt nur aktive Mitarbeiter. Bei Einträgen, die ein Administrator für jemand anderen anlegt oder ändert, steht der Administrator als „angelegt von“ bzw. „geändert von“ im Datensatz. Normale Benutzer haben die Auswahl nicht und können die Liste der Mitarbeiter auch nicht über die API abrufen.

### Benutzer löschen

**Löschen** (Button oder Rechtsklick) entfernt einen Benutzer endgültig. Das geht nur, wenn er **keine Zeiteinträge** hat, zum Beispiel bei einem falsch angelegten Konto oder einem Testkonto. Projektzuordnungen werden mit gelöscht. Hat der Benutzer Zeiteinträge, lehnt das Backend das Löschen ab und nennt die Anzahl. Der Grund: Die Datenbank würde sonst alle Zeiteinträge mitlöschen, und Berichte und Abrechnung beruhen darauf. In diesem Fall bleibt nur **Deaktivieren**. Das eigene Konto kann ein Administrator nicht löschen. Vor jedem Löschen fragt das Tool nach, und es gibt kein Rückgängig. Wer versehentlich gelöscht hat, kann den Benutzer nur aus einer Datensicherung wiederherstellen.

### Adminrecht ändern

**Bearbeiten** → Haken **Administrator** setzen oder entfernen → Speichern. Die Änderung gilt sofort, auch für bereits angemeldete Personen.

## Für Anwender

### Anmelden

1. Web-App öffnen, Adresse `/timesheet/login`.
2. Benutzername und Passwort eingeben.

Nach 5 falschen Versuchen ist das Konto **15 Minuten** gesperrt, auch mit dem richtigen Passwort. Die Fehlermeldung ist immer dieselbe. Sie sagt nicht, ob der Benutzername existiert. Wer sich ausgesperrt hat, wartet 15 Minuten oder bittet einen Administrator um ein Einmalpasswort.

### Erste Anmeldung mit Einmalpasswort

1. Mit Benutzername und Einmalpasswort anmelden.
2. Die Web-App zeigt „Choose a new password“. Als aktuelles Passwort das Einmalpasswort eingeben.
3. Ein neues Passwort wählen: mindestens **10 Zeichen**, ohne Leerzeichen am Anfang oder Ende, höchstens 128 Zeichen. Es muss sich vom alten unterscheiden.
4. Erst danach ist die Zeiterfassung freigeschaltet.

### Passwort später ändern

In der Web-App oben **Change password** klicken (Adresse `/timesheet/change-password`). Das aktuelle Passwort ist nötig. Nach dem Wechsel werden alle anderen Anmeldungen der Person beendet.

### Sitzung

Eine Anmeldung gilt standardmäßig 8 Stunden. Danach leitet die Web-App auf die Login-Seite um. **Log out** beendet die Sitzung sofort.

## Erste Einrichtung (ersten Administrator anlegen)

Bevor die Anmeldung erzwungen wird, muss es ein Administrator-Konto geben. Solange in `backend/.env` `AUTH_ENABLED=false` steht (Standard), fragt das Admin-Tool nicht nach einem Login und die API lässt alles durch.

1. Backend starten, Admin-Tool öffnen. Es erscheint kein Login-Fenster.
2. Den eigenen Mitarbeiter bearbeiten: Benutzername eintragen, Haken **Administrator** setzen, speichern.
3. **Einmalpasswort** klicken und das Passwort notieren.
4. In der Web-App unter `/timesheet/login` anmelden und das Einmalpasswort durch ein eigenes ersetzen. Damit ist geprüft, dass alles funktioniert.
5. In `backend/.env` setzen:
   - `AUTH_ENABLED=true`
   - `SECRET_KEY=<mindestens 32 Zeichen>` (erzeugen mit `python -c "import secrets; print(secrets.token_hex(32))"`)
6. Backend neu starten. Ohne gültigen `SECRET_KEY` startet die App absichtlich nicht.
7. Ab jetzt verlangt auch das Admin-Tool beim Start einen Login. Nur Konten mit Adminrecht kommen hinein.

Das Admin-Tool bietet keinen eigenen Passwortwechsel für die Person, die gerade angemeldet ist. Administratoren ändern ihr Passwort in der Web-App unter „Change password“.

### Wenn der einzige Administrator ausgesperrt ist

Es gibt keinen Selbstweg. Wer Zugriff auf `backend/.env` hat, kann so vorgehen:

1. `AUTH_ENABLED=false` setzen, Backend neu starten.
2. Im Admin-Tool **Einmalpasswort** für das Konto setzen.
3. `AUTH_ENABLED=true` setzen, Backend neu starten.

Die `.env` muss deshalb geschützt bleiben.

## Sicherheitshinweise

- **HTTPS:** In Produktion muss die Web-App über HTTPS laufen (TLS am Reverse Proxy, siehe [INSTALL_IIS_INTRANET.md](INSTALL_IIS_INTRANET.md)) und in `backend/.env` `COOKIE_SECURE=true` gelten. Nur dann werden die Anmelde-Cookies ausschließlich verschlüsselt übertragen. Nur für lokale Entwicklung über `http://` steht `COOKIE_SECURE=false`.
- **Einmalpasswörter** nur auf sicherem Weg weitergeben und nicht in Chats oder unverschlüsselten Mails.
- **Datensicherungen** der Tabelle `employees` (Datenbank-Backup und Datei-Export) enthalten die Passwort-Hashes. Diese Dateien wie Zugangsdaten behandeln und nicht frei ablegen.
- **Testkonto:** In der Datenbank gibt es das Konto `testheini` („Testheini Testkonto“) für Tests. Wer es nicht braucht, deaktiviert es im Admin-Tool.

## Häufige Fragen

**Warum kann sich jemand nicht anmelden?**
Prüfe in der Benutzerliste: Ist ein Benutzername eingetragen, ein Passwort gesetzt und **Aktiv** angehakt? Wenn ja, war die Person eventuell wegen Fehlversuchen 15 Minuten gesperrt. Ein neues Einmalpasswort hebt die Sperre auf.

**Kann ich ein Passwort ansehen?**
Nein. Es ist nur als Hash gespeichert. Man kann es nur ersetzen (Einmalpasswort).

**Das Einmalpasswort ist weg, bevor ich es weitergegeben habe.**
Einfach ein neues Einmalpasswort setzen. Das alte ist damit ungültig.

**Warum sieht jemand die Daten von Kollegen nicht?**
Normale Benutzer sehen nur ihre eigenen Zeiteinträge. Nur Administratoren haben Zugriff auf alle.

**Was passiert mit den Zeiteinträgen, wenn ich einen Benutzer deaktiviere?**
Nichts. Deaktivieren sperrt nur die Anmeldung. Alle Einträge bleiben erhalten.
