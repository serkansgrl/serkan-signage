# Serkan Signage — Deutsch

**Selbst gehostete Digitalanzeige für Zuhause, Büros und Informationsbildschirme.**

[English](README.md) · [Türkçe](README.tr.md)

## Was macht Serkan Signage?

Eine auf einem eigenen Server laufende Web-Anwendung mit **Fotodiashow, Wochen-Speiseplan, Wettervorhersage, RSS-Nachrichten und fünf täglichen Quizfragen**. Die Anzeige ist für Fernseher und Tablets optimiert. Im automatischen TV-Modus wechseln sich Nachrichten und Quiz ab; bei Quizfragen erscheint kurz vor dem Wechsel die richtige Antwort.

### Funktionen

- **Fotos:** Bilder im Verwaltungsbereich hochladen oder einen NAS-Ordner schreibgeschützt einbinden
- **Speiseplan:** Mahlzeiten für Montag bis Sonntag verwalten
- **Wetter:** siebentägige Vorhersage von Open-Meteo, Ort und Koordinaten einstellbar
- **Nachrichten:** BR24 als voreingestellte RSS-Quelle; Feed-URLs und erlaubte Nachrichten-Domains einstellbar
- **Tagesquiz:** fünf deutschsprachige Multiple-Choice-Fragen pro Tag
- **TV-Modus:** automatische Rotation der Nachrichten und Fragen
- **Verwaltung:** Passwortbereich unter `/serkan`
- **PWA:** als Web-App installierbar; Vollbildmodus verfügbar

**Hinweis:** Die Benutzeroberfläche und das Quiz sind derzeit auf Deutsch. Die Projektanleitung steht in drei Sprachen zur Verfügung.

## Voraussetzungen

Docker Engine mit Docker Compose, ein freier Port (standardmäßig 8098) und optional ein bereits auf dem Docker-Host eingehängtes NAS-Verzeichnis.

## Installation

```sh
git clone https://github.com/serkansgrl/serkan-signage.git
cd serkan-signage
cp .env.example .env
```

**Unbedingt `.env` bearbeiten:** `INITIAL_ADMIN_PASSWORD` durch ein eigenes, sicheres Passwort mit mindestens zwölf Zeichen ersetzen.

```sh
docker compose up -d --build
docker compose ps
```

Anzeige auf dem **Docker-Host:** `http://127.0.0.1:8098/` — Verwaltung: `http://127.0.0.1:8098/serkan`.

Aus Sicherheitsgründen ist die Standardbindung **nur localhost**. Für andere Geräte im vertrauenswürdigen LAN `BIND_ADDRESS=0.0.0.0` einstellen und den Zugriff mit einer Firewall einschränken. Für das Internet eine HTTPS-Reverse-Proxy-Verbindung verwenden und `COOKIE_SECURE=true` setzen. Einen zusätzlichen Zugriffsschutz für die Verwaltung empfehlen wir.

Das Startpasswort wird nur bei der **ersten Einrichtung** eines leeren Datenvolumes verwendet. Spätere Änderungen in `.env` setzen ein vorhandenes Passwort nicht zurück.

## Daten, NAS und Sicherheit

Das Docker-Volume `signage_data` enthält hochgeladene Bilder, Konfiguration, Passwort-Hash und Sitzungsschlüssel. Dieses Volume vertraulich sichern, niemals auf GitHub hochladen.

Für NAS-Fotos das Verzeichnis zunächst auf dem Host einhängen (vorzugsweise SMB3 oder NFS), dann den Hostpfad über `NAS_PHOTOS_PATH` setzen. Der Container liest diesen Ordner nur schreibgeschützt. Er benötigt keine NAS-Anmeldedaten.

Die Anzeige, Bilder und die Daten-APIs sind **öffentlich für jeden, der den Server erreicht**. Nur die Verwaltungsfunktionen sind passwortgeschützt. Daher keine privaten Bilder auf einer ungeschützt öffentlich erreichbaren Instanz verwenden.

## Wichtige Umgebungsvariablen

- `INITIAL_ADMIN_PASSWORD`: erstes Administratorpasswort (mindestens zwölf Zeichen)
- `BIND_ADDRESS`: `127.0.0.1` oder LAN-Bindung `0.0.0.0`
- `HTTP_PORT`: standardmäßig `8098`
- `COOKIE_SECURE`: bei HTTPS `true`
- `FRAME_ANCESTORS`: erlaubte Webseiten-Ursprünge für die Einbettung der **Anzeige**, nicht des Admin-Bereichs
- `NAS_PHOTOS_PATH`: Fotoverzeichnis auf dem Docker-Host
- `NEWS_FEEDS`, `NEWS_ALLOWED_HOSTS`, `NEWS_SOURCE_LABEL`: anpassbare Nachrichtenquellen
- `TZ`: Zeitzone, standardmäßig `Europe/Berlin`

## Updates und Tests

```sh
python3 -m unittest discover -s tests -v
docker compose config
docker compose up -d --build
```

Weitere Hinweise: [Security](SECURITY.md) · [Migration](MIGRATION.md) · [Lizenz](LICENSE). Drittanbieter-Nachrichten und Medien unterliegen ihren eigenen Nutzungsbedingungen.
