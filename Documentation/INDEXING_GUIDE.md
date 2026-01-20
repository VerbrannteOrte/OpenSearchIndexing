# Datei-Indexierung - Vollständige Anleitung

## Überblick

Der Indexer unterstützt umfassende Dateiverarbeitung mit:

✅ **Mehrere Verzeichnisse** gleichzeitig indexieren  
✅ **Office-Formate**: LibreOffice (.odt, .ods, .odp) und MS Office (.doc, .docx, .xls, .xlsx, .ppt, .pptx)  
✅ **PDFs** mit automatischer OCR-Erkennung für gescannte Dokumente  
✅ **Bilder** (.png, .jpg, .tif) mit OCR-Texterkennung  
✅ **Automatische Überwachung** für neue Dateien  
✅ **Flexible Filter** nach Dateityp und Ausschlussmustern  

## Schnellstart

### 1. Verzeichnis-Verwaltung öffnen

```
http://localhost:8080/directories.html
```

### 2. Erstes Verzeichnis hinzufügen

Klicken Sie auf **"➕ Verzeichnis hinzufügen"** und konfigurieren Sie:

- **ID**: `company_docs`
- **Pfad**: `/mnt/company/documents`
- **Beschreibung**: `Firmen-Dokumente`
- **Dateitypen**: MS Office, LibreOffice, PDF
- **Rekursiv**: ✅ (Unterverzeichnisse einbeziehen)
- **Überwachen**: ❌ (nur einmalige Indexierung)

### 3. Indexierung starten

Nach dem Hinzufügen startet die Indexierung automatisch beim nächsten Neustart des Indexers, oder triggern Sie manuell:

```bash
docker-compose restart indexer
```

## Unterstützte Dateiformate

### Office-Dokumente

**LibreOffice:**
- `.odt` - Text (Writer)
- `.ods` - Tabellen (Calc)
- `.odp` - Präsentationen (Impress)
- `.odg` - Zeichnungen (Draw)
- `.odf` - Formeln (Math)

**Microsoft Office:**
- `.doc`, `.docx` - Word-Dokumente
- `.xls`, `.xlsx` - Excel-Tabellen
- `.ppt`, `.pptx` - PowerPoint-Präsentationen
- `.docm`, `.xlsm`, `.pptm` - Makro-Dateien

### PDFs

- `.pdf` - Portable Document Format
- **Automatische OCR**: Wenn ein PDF wenig Text enthält (< 100 Zeichen), wird automatisch OCR durchgeführt
- **300 DPI Auflösung** für optimale Texterkennungsqualität

### Bilder (mit OCR)

- `.png` - Portable Network Graphics
- `.jpg`, `.jpeg` - JPEG-Bilder
- `.tif`, `.tiff` - TIFF-Bilder
- `.bmp` - Bitmap-Bilder
- `.gif` - GIF-Bilder

**OCR-Sprachen:**
- Deutsch (deu)
- Englisch (eng)
- Französisch (fra)
- Spanisch (spa)
- Italienisch (ita)

### Andere Formate

- `.txt` - Textdateien
- `.md` - Markdown
- `.csv` - CSV-Dateien
- `.json` - JSON-Dateien
- `.xml` - XML-Dateien
- `.html`, `.htm` - HTML-Dateien
- `.eml`, `.msg` - E-Mails

## Verzeichnis-Konfiguration

### Beispiel 1: Dokumenten-Archiv

```json
{
  "id": "archive",
  "path": "/mnt/archive",
  "description": "Dokumenten-Archiv",
  "enabled": true,
  "recursive": true,
  "watch": false,
  "file_types": ["all"],
  "exclude_patterns": ["*.tmp", "*.bak", ".git/*"]
}
```

### Beispiel 2: Scan-Ordner mit OCR

```json
{
  "id": "scans",
  "path": "/mnt/scans",
  "description": "Gescannte Dokumente",
  "enabled": true,
  "recursive": true,
  "watch": true,
  "file_types": ["images", "pdf"],
  "exclude_patterns": []
}
```

### Beispiel 3: Nur Office-Dokumente

```json
{
  "id": "office",
  "path": "/mnt/office",
  "description": "Office-Dateien",
  "enabled": true,
  "recursive": true,
  "watch": false,
  "file_types": ["microsoft_office", "libreoffice"],
  "exclude_patterns": ["*/temp/*", "~$*"]
}
```

## Konfigurationsoptionen

### Dateityp-Filter

- `all` - Alle Dateitypen
- `microsoft_office` - Word, Excel, PowerPoint
- `libreoffice` - ODF-Formate
- `pdf` - PDF-Dateien
- `images` - Bilder mit OCR
- `text` - Textdateien
- `email` - E-Mail-Formate
- `archives` - ZIP, TAR, etc.

### Ausschlussmuster

Verwenden Sie Unix-Glob-Muster:

```
*.tmp           # Alle .tmp Dateien
*.bak           # Backup-Dateien
.git/*          # Git-Verzeichnis
__pycache__/*   # Python-Cache
*/temp/*        # Alle temp-Verzeichnisse
~$*             # Temporäre Office-Dateien
```

### Rekursiv vs. Nicht-Rekursiv

**Rekursiv (✅)**:
```
/documents/
├── file1.pdf       ✓ indexiert
├── subdir/
│   └── file2.pdf   ✓ indexiert
```

**Nicht-Rekursiv (❌)**:
```
/documents/
├── file1.pdf       ✓ indexiert
├── subdir/
│   └── file2.pdf   ✗ NICHT indexiert
```

### Überwachung (Watch)

**Aktiviert (✅)**:
- Verzeichnis wird kontinuierlich überwacht
- Neue Dateien werden automatisch indexiert
- Geänderte Dateien werden re-indexiert
- Ideal für: Scan-Ordner, Upload-Verzeichnisse

**Deaktiviert (❌)**:
- Nur einmalige Indexierung beim Start
- Keine automatische Erkennung neuer Dateien
- Ideal für: Archive, statische Dokumente

## OCR-Funktionalität

### Automatische OCR für Bilder

Alle Bilder werden automatisch mit OCR verarbeitet:

```python
# Wird automatisch durchgeführt
image.png → OCR → "Extrahierter Text"
```

### Intelligente PDF-OCR

PDFs werden intelligent verarbeitet:

1. **Tika-Extraktion**: Versucht zuerst normale Textextraktion
2. **OCR-Erkennung**: Wenn < 100 Zeichen gefunden → PDF ist wahrscheinlich gescannt
3. **OCR-Verarbeitung**: Konvertiert zu Bildern (300 DPI) und führt OCR durch

```python
# Beispiel-Workflow
scanned.pdf 
  → Tika: "15 Zeichen gefunden"
  → OCR wird getriggert
  → Konvertiere zu Bildern
  → OCR Seite 1, 2, 3...
  → "5000 Zeichen extrahiert"
```

### OCR-Qualität optimieren

**Für beste Ergebnisse:**

1. **Scan-Auflösung**: Mindestens 300 DPI
2. **Bild-Format**: TIFF oder PNG (verlustfrei)
3. **Kontrast**: Hoher Kontrast zwischen Text und Hintergrund
4. **Ausrichtung**: Gerade ausgerichtete Seiten
5. **Sprache**: Korrekte Sprache im Dokument

**Schlechte OCR-Ergebnisse vermeiden:**
- ❌ Niedrige Auflösung (< 200 DPI)
- ❌ JPEG mit hoher Kompression
- ❌ Unscharfe oder verschwommene Bilder
- ❌ Handschrift (nur Druckschrift funktioniert gut)
- ❌ Komplexe Layouts mit vielen Spalten

## Docker-Volume-Mapping

### Beispiel docker-compose.yml

```yaml
services:
  indexer:
    volumes:
      # Lokales Verzeichnis → Container-Pfad
      - /pfad/auf/host/dokumente:/mnt/documents:ro
      - /pfad/auf/host/scans:/mnt/scans:ro
      - /pfad/auf/host/archiv:/mnt/archive:ro
      - ./config:/config
      - ./ontologies:/ontologies
```

### Konfiguration anpassen

Dann in der Admin-UI:

1. Verzeichnis `/mnt/documents` hinzufügen
2. Verzeichnis `/mnt/scans` hinzufügen (mit Überwachung)
3. Verzeichnis `/mnt/archive` hinzufügen

## Monitoring und Logs

### Indexierungs-Logs anzeigen

```bash
# Live-Logs ansehen
docker-compose logs -f indexer

# Nach spezifischen Dateien suchen
docker-compose logs indexer | grep "indexiert"

# OCR-Aktivität prüfen
docker-compose logs indexer | grep "OCR"
```

### Fortschritt überwachen

Der Indexer loggt:
```
INFO - Starte Indexierung: /mnt/documents (rekursiv: True)
INFO - Indexiere: /mnt/documents/contract.pdf (PDF)
INFO - Führe OCR für Bild durch: /mnt/scans/scan001.png
INFO - OCR erfolgreich für scan001.png: 2345 Zeichen extrahiert
INFO - PDF OCR erfolgreich: 15 Seiten, 12500 Zeichen
INFO - ✓ Datei indexiert: contract.pdf (OCR: True, Konzepte: 5)
INFO - ✓ Verzeichnis abgeschlossen: /mnt/documents (150 indexiert, 5 übersprungen)
```

## Performance-Optimierung

### OCR ist langsam

OCR ist rechenintensiv. Für bessere Performance:

1. **Separate Worker**: Dedizierter Container nur für OCR
2. **GPU-Beschleunigung**: Tesseract mit GPU-Support
3. **Batch-Verarbeitung**: Nachts indexieren
4. **Selektive OCR**: Nur Bilder/PDFs in bestimmten Ordnern

### Große Verzeichnisse

Bei 1000+ Dateien:

1. **Exclude-Patterns nutzen**: Temporäre Dateien ausschließen
2. **Nicht-rekursiv**: Erst Top-Level, dann Unterverzeichnisse
3. **Dateityp-Filter**: Nur relevante Formate
4. **Batch-Indexierung**: Verzeichnisse nacheinander

## Troubleshooting

### Dateien werden nicht indexiert

**Prüfen Sie:**

1. Ist das Verzeichnis aktiviert? (enabled: true)
2. Existiert der Pfad im Container?
   ```bash
   docker-compose exec indexer ls -la /mnt/documents
   ```
3. Wird der Dateityp unterstützt?
4. Greift ein Ausschlussmuster?

### OCR funktioniert nicht

**Prüfen Sie:**

1. Tesseract installiert?
   ```bash
   docker-compose exec indexer tesseract --version
   ```
2. Sprachen verfügbar?
   ```bash
   docker-compose exec indexer tesseract --list-langs
   ```
3. Logs prüfen:
   ```bash
   docker-compose logs indexer | grep "OCR Fehler"
   ```

### Duplikate werden indexiert

Der Indexer verwendet SHA256-Hashes zur Duplikat-Erkennung. Duplikate sollten nicht auftreten, außer:

- Datei wurde geändert (neuer Hash)
- Index wurde gelöscht
- Hash-Berechnung fehlgeschlagen

## API-Endpunkte

```bash
# Alle Verzeichnisse abrufen
GET /admin/directories

# Verzeichnis hinzufügen
POST /admin/directories
{
  "id": "docs",
  "path": "/mnt/docs",
  "enabled": true,
  "recursive": true,
  "watch": false,
  "file_types": ["pdf", "microsoft_office"],
  "exclude_patterns": ["*.tmp"]
}

# Verzeichnis aktualisieren
PUT /admin/directories/{id}
{
  "enabled": false
}

# Verzeichnis löschen
DELETE /admin/directories/{id}

# Unterstützte Dateitypen
GET /admin/supported-file-types

# Indexierung triggern
POST /admin/trigger-indexing
```

## Best Practices

### 1. Verzeichnis-Struktur

```
/mnt/
├── documents/      # Finale Dokumente (nicht überwacht)
├── scans/          # Neue Scans (überwacht, mit OCR)
├── uploads/        # User-Uploads (überwacht)
└── archive/        # Archiv (deaktiviert)
```

### 2. Dateityp-Strategie

- **Scan-Ordner**: Nur `images` und `pdf` (mit OCR)
- **Office-Ordner**: Nur `microsoft_office` und `libreoffice`
- **Gemischt**: `all`, aber mit Exclude-Patterns

### 3. Überwachung

- **Überwachen**: Nur aktive Upload-/Scan-Ordner
- **Nicht überwachen**: Archive, statische Dokumente
- **Grund**: Spart Ressourcen

### 4. Exclude-Patterns

Immer ausschließen:
```
*.tmp
*.bak
~$*
.git/*
__pycache__/*
.DS_Store
Thumbs.db
```

## Erweiterte Konfiguration

### Beispiel: Multi-Tenant-Setup

```json
{
  "directories": [
    {
      "id": "tenant_a",
      "path": "/mnt/tenants/a/documents",
      "description": "Firma A",
      "enabled": true,
      "file_types": ["all"]
    },
    {
      "id": "tenant_b",
      "path": "/mnt/tenants/b/documents",
      "description": "Firma B",
      "enabled": true,
      "file_types": ["all"]
    }
  ]
}
```

### Beispiel: Sprach-spezifische Ordner

```json
{
  "id": "german_docs",
  "path": "/mnt/docs/de",
  "file_types": ["pdf"],
  "ocr_language": "deu"
},
{
  "id": "english_docs",
  "path": "/mnt/docs/en",
  "file_types": ["pdf"],
  "ocr_language": "eng"
}
```

## Zusammenfassung

✅ Verzeichnisse in Admin-UI konfigurieren  
✅ Dateitypen gezielt auswählen  
✅ OCR läuft automatisch für Bilder und gescannte PDFs  
✅ Überwachung für Upload-Ordner aktivieren  
✅ Exclude-Patterns für temporäre Dateien nutzen  
✅ Logs monitoren für Troubleshooting  

Für weitere Fragen siehe Logs oder GitHub Issues.
