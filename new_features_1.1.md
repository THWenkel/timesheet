# Ich habe zwei Aufgaben zu erledigen

1. Aufgabe: Einführung eines neuen Admin-Menüs für Datensicherung und Wiederherstellung

## Backup in der Datenbank selbst

Es gibt in der Datenbank WiTERP bereits eine dbo.timesheet_entries_backup Tabelle, genauso für dbo.employees_backup. Diese sind die Backup-Tabellen für die beiden Tabellen dbo.employees und dbo.timesheet.entries.
Ich brauche noch weitere Sicherungstabellen für dbo.customers, dbo.employees, dbo.projects etc. Ich brauche im Admin-Tool ein Menü und dort soll es unter anderem einen Eintrag für Datensicherung geben. Es soll ein neues Fenster geöffnet werden, in dem ein neuer Button Sicherung (englisch Backup) sichtbar ist, der auf Knopfdruck eine Sicherung aller Daten in die vorher genannten Backup-Tabellen macht.
Ich hätte gerne mehrere Checkboxen, um auch nur einzelne Tabellen zu sichern.

## Backup im Dateisystem

Es muss auch noch einen weiteren Button geben, der Sicherungen der Daten in CSV und/oder JSON Daten macht. Es soll ein Dialogfenster erscheinen, das nach einem Pfad fragt, wo die Daten abgelegt werden sollen. Der Pfad selbst soll sich das Admin-Tool merken und beim nächsten Mal selbstständig anbieten als Verzeichnis. Natürlich sollen auch mehrere Datenstände im Dateisystem parallel abgespeichert werden können. Via Checkboxen soll es auch die Möglichkeit geben, nur einzelne Tabellen Daten zu sichern.

Wichtig ist, dass die Daten sicher, mit Timestamp im Dateinamen versehen, abgespeichert werden. 
Diese Daten sollen für externe Backups genutzt werden, losgelöst von den anderen Backup-Möglichkeiten in der DB selbst (DB-Server Failure, etc.).
Wichtig: Alle Tabellen-Daten sollten in einzelnen CSV/JSON Dateien gesichert werden.

Wiederherstellung nach Fehler(n):
Natürlich ist es ebenfalls sehr wichtig, auch solche Daten wiederherstellen zu können.
Wichtig zuerst: Der Anwender muss Wiederherstellungen extra bestätigen (Auflistung, welche Daten wiederhergestellt werden). Nicht das versehentlich alte Daten wiederhergestellt werden. Also wichtig als Meldung: "Sind sie sich wirklich sicher!?"
Wiederherstellungen können über verschiedene Wege erfolgen:

- Wiederherstellungen direkt auf dem Datenbankserver, durch wiederherstellen der Daten aus den _backup Tabellen. Auch hier ist es sehr wichtig, das auch nur einzelne Tabellen wiederhergestellt werden können.
- Wiederherstellen der Daten aus externen CSV/JSON Daten. Es muss eine Import-Möglichkeit geben, die es erlaubt, die Daten wieder in die entsprechenden Tabellen zu importieren.

Sehr wichtig ist, das wir zunächst nur Testing für die Sicherung machen. Wiederherstellungen werden explizit erst später gemacht! Hier bitte sehr aufpassen bei den Tests.

2. Aufgabe:

Beschreibung: Einführung eines sicheren Login-Mechanismus für die Web-Anwendung

## Sicherstellung eines sicheren Logins

Die Web-Anwendung muss einen sicheren Login-Mechanismus implementieren, um unbefugten Zugriff zu verhindern.

## Anforderungen

- Der Login muss über eine sichere Verbindung (HTTPS) erfolgen.
- Die Anmeldung muss via JWT (JSON Web Token) erfolgen, um die Authentifizierung sicher zu gestalten.

## Umsetzung

- Implementierung eines sicheren Login-Formulars in der Web-Anwendung.
- Sicherstellung, dass die JWT-Tokens sicher gespeichert und übertragen werden.
- Anwender müssen sich mit ihren Zugangsdaten anmelden, um Zugriff auf die Web-Anwendung zu erhalten. Sie müssen außerdem eine Möglichkeit haben, ihr Passwort zurückzusetzen oder zu ändern.

## Zusammenfassung

Prüfe, ob der sichere Login-Mechanismus korrekt implementiert ist und die Anforderungen erfüllt werden.
Nutze dafür einen Test-Account Testheini mit den entsprechenden Zugangsdaten.
führe die Tests mit dem Test-Account durch, um sicherzustellen, dass der Login-Mechanismus korrekt funktioniert.