# Beware: untested AI coded Project !! 
# OpenSearch Document Indexing System

Vollständiges Dokumenten-Indexierungs-System mit:

- ✅ Multi-Directory Support
- ✅ OCR (Tesseract + EasyOCR)
- ✅ Sütterlin-Erkennung für historische Dokumente
- ✅ GPU-Beschleunigung
- ✅ Erweiterte Metadaten-Extraktion
- ✅ Dynamische Facetten-Verwaltung
- ✅ SKOS-Ontologien
- ✅ Web-Crawler
- ✅ REST API

## Schnellstart
```bash
./Scripts/setup.sh
./Scripts/start.sh
open http://localhost:8080
```
## Anpassung
- In den HTML Dateien die API URL anpassen.
- Die docker-compose.yml anpassen
- "index.highlight.max_analyzed_offset": 10000000 im OpenSearchDashboard setzen
- "index.mapping.total_fields.limit": "1500" im OpenSearchDashboard setzen

## Dokumentation

- `Documentation/INDEXING_GUIDE.md` - Datei-Indexierung
- `Documentation/FACETS_GUIDE.md` - Facetten-Verwaltung
- `Documentation/ADVANCED_FEATURES.md` - OCR & Sütterlin

## Lizenz

MIT

## ToDo
- OpenSearch IndexSettings im Docker übergeben.
- URLS per Variablen konfigurieren.
- Nächste Seite im Search_ui hinzufügen
- Direkte Ansicht der Dokumente
