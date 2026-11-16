# Serkan Signage — Deutsch

**Selbst gehostetes Digital-Signage- und Informations-Dashboard für Zuhause, Büros und Displays.**

> **Projektstatus: Vorbereitung.** Der öffentliche Quellcode der Anwendung wurde noch nicht sicherheitsgeprüft und ist deshalb noch nicht enthalten. Die Dateien in diesem Repository sind derzeit ein Docker-/Dokumentationsgerüst, **keine sofort nutzbare Anwendung**.

## Funktionen der vorhandenen privaten Installation
- **Fotos:** automatische Diashow aus einem lokalen Verzeichnis; NAS-Freigaben lassen sich auf dem Docker-Host einhängen.
- **Speiseplan:** Darstellung und Verwaltung von Menü- oder Essensinformationen.
- **Wetter:** Wetterdaten über Open-Meteo.
- **Nachrichten:** RSS-Nachrichten, aktuell unter anderem aus BR24.
- **Tagesquiz:** fünf tägliche Fragen und automatische Wiedergabe im TV-Modus.
- **TV-Modus:** wechselnde Inhalte für einen Bildschirm ohne ständige Bedienung.
- **Administration:** passwortgeschützter Verwaltungsbereich.
- **PWA:** Installation als Web-App auf unterstützten Geräten.

## Technischer Aufbau
Ein kompakter Python-Webserver liefert die Benutzeroberfläche. Docker erleichtert Betrieb und Updates. Konfiguration, geheime Schlüssel und Bilder müssen getrennt vom veröffentlichten Quellcode gespeichert werden. Für öffentlich erreichbare Installationen werden HTTPS, Zugriffsschutz für die Administration und sichere Sitzungscookies empfohlen.

## Geplante Docker-Installation
```bash
cp .env.example .env
docker compose up -d --build
```
**Noch nicht ausführbar:** Der geprüfte Anwendungscode und die endgültige Volume-/Konfigurationsstruktur fehlen derzeit.

## Veröffentlichung
Vor der Freigabe müssen feste IP-Adressen, lokale NAS-Pfade und persönliche Einstellungen durch konfigurierbare Werte ersetzt, echte Geheimnisse ausgeschlossen und die Anwendung getestet werden.

Weitere Informationen: [English](README.md) · [Türkçe](README.tr.md) · [Sicherheit](SECURITY.md).
