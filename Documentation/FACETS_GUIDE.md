# Facetten-Verwaltung - Anleitung

## Überblick

Die Facetten-Verwaltung ermöglicht es Ihnen, die Filter in der Suchansicht dynamisch anzupassen:

✅ Facetten hinzufügen/entfernen  
✅ Reihenfolge per Drag & Drop ändern  
✅ Facetten aktivieren/deaktivieren  
✅ Ontologien als Facetten nutzen  
✅ Icons und Labels anpassen  

## Schnellstart

### 1. Admin-UI öffnen

```
http://localhost:8080/admin.html
```

### 2. Eigene Facette erstellen

**Beispiel: Berufe als Facette**

1. Klicken Sie auf **"➕ Neue Facette"**
2. Füllen Sie das Formular aus:
   - **ID**: `professions`
   - **Label**: `Berufe`
   - **Icon**: `👔` (aus der Auswahl)
   - **Feld-Name**: `professions`
   - **Typ**: `Terms`
   - **Anzahl**: `50`
3. Klicken Sie auf **"Hinzufügen"**

### 3. Facette aus Ontologie erstellen

**Beispiel: Berufe-Taxonomie**

1. Erstellen Sie die Ontologie (siehe unten)
2. Klicken Sie auf **"🏷️ Aus Ontologie"**
3. Wählen Sie die Ontologie `professions`
4. Geben Sie Label und Icon ein
5. Klicken Sie auf **"Erstellen"**

## Ontologie für Berufe erstellen

### JSON-Format

Erstellen Sie `ontologies/professions.json`:

```json
{
  "id": "professions",
  "label": "Berufe",
  "children": [
    {
      "id": "it",
      "label": "IT und Technologie",
      "children": [
        {
          "id": "developer",
          "label": "Entwickler",
          "aliases": ["Programmierer", "Software Engineer", "Developer"]
        },
        {
          "id": "data_scientist",
          "label": "Data Scientist",
          "aliases": ["Datenwissenschaftler", "ML Engineer"]
        },
        {
          "id": "devops",
          "label": "DevOps Engineer",
          "aliases": ["System Administrator"]
        }
      ]
    },
    {
      "id": "business",
      "label": "Business",
      "children": [
        {
          "id": "manager",
          "label": "Manager",
          "aliases": ["Geschäftsführer", "CEO"]
        },
        {
          "id": "consultant",
          "label": "Berater",
          "aliases": ["Consultant"]
        }
      ]
    },
    {
      "id": "healthcare",
      "label": "Gesundheitswesen",
      "children": [
        {
          "id": "doctor",
          "label": "Arzt",
          "aliases": ["Doktor", "Mediziner"]
        },
        {
          "id": "nurse",
          "label": "Krankenpfleger",
          "aliases": ["Pfleger"]
        }
      ]
    }
  ]
}
```

### SKOS-Format (Turtle)

Alternativ als `ontologies/professions.ttl`:

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prof: <http://example.org/professions/> .

prof:Developer
    a skos:Concept ;
    skos:prefLabel "Entwickler"@de ;
    skos:altLabel "Programmierer"@de ;
    skos:altLabel "Software Engineer"@en .

prof:Manager
    a skos:Concept ;
    skos:prefLabel "Manager"@de ;
    skos:altLabel "Geschäftsführer"@de ;
    skos:altLabel "CEO"@en .

prof:Doctor
    a skos:Concept ;
    skos:prefLabel "Arzt"@de ;
    skos:altLabel "Doktor"@de ;
    skos:altLabel "Mediziner"@de .
```

## OpenSearch Mapping aktualisieren

Damit die Facette funktioniert, muss das Dokument-Feld im Index existieren.

### Option 1: Automatisch durch Indexer

Der Indexer extrahiert automatisch Konzepte aus Ihren Ontologien und speichert sie im Dokument.

### Option 2: Manuell hinzufügen

Wenn Sie eigene Felder verwenden möchten, fügen Sie sie zum Index-Mapping hinzu:

```python
# In indexer.py, _create_index() Methode
"professions": {
    "type": "keyword"
}
```

Dann beim Indexieren Werte zuweisen:

```python
doc = {
    'title': 'CV - John Doe',
    'content': '...',
    'professions': ['Entwickler', 'Data Scientist'],  # ← Neue Facette
    # ...
}
```

## Weitere Beispiele

### Branchen/Industries

```json
{
  "id": "industries",
  "label": "Branchen",
  "children": [
    {"id": "tech", "label": "Technologie"},
    {"id": "finance", "label": "Finanzen"},
    {"id": "healthcare", "label": "Gesundheitswesen"},
    {"id": "education", "label": "Bildung"},
    {"id": "retail", "label": "Einzelhandel"}
  ]
}
```

### Unternehmensgrößen

```json
{
  "id": "company_size",
  "label": "Unternehmensgröße",
  "children": [
    {"id": "startup", "label": "Startup (1-10)"},
    {"id": "small", "label": "Klein (11-50)"},
    {"id": "medium", "label": "Mittel (51-250)"},
    {"id": "large", "label": "Groß (251-1000)"},
    {"id": "enterprise", "label": "Konzern (1000+)"}
  ]
}
```

### Standorte

```json
{
  "id": "locations",
  "label": "Standorte",
  "children": [
    {
      "id": "germany",
      "label": "Deutschland",
      "children": [
        {"id": "berlin", "label": "Berlin"},
        {"id": "munich", "label": "München"},
        {"id": "hamburg", "label": "Hamburg"}
      ]
    },
    {
      "id": "austria",
      "label": "Österreich",
      "children": [
        {"id": "vienna", "label": "Wien"},
        {"id": "salzburg", "label": "Salzburg"}
      ]
    }
  ]
}
```

### Skills/Fähigkeiten

```json
{
  "id": "skills",
  "label": "Fähigkeiten",
  "children": [
    {
      "id": "programming",
      "label": "Programmierung",
      "children": [
        {"id": "python", "label": "Python"},
        {"id": "javascript", "label": "JavaScript"},
        {"id": "java", "label": "Java"}
      ]
    },
    {
      "id": "languages",
      "label": "Sprachen",
      "children": [
        {"id": "german", "label": "Deutsch"},
        {"id": "english", "label": "Englisch"},
        {"id": "french", "label": "Französisch"}
      ]
    }
  ]
}
```

## Facetten-Konfiguration

### Facetten-Typen

- **terms**: Standard für kategorische Werte (z.B. Berufe, Dateitypen)
- **range**: Für Zahlenbereiche (z.B. Gehalt, Dateigröße)
- **date_histogram**: Für Zeiträume (z.B. Jahr, Monat)

### Display-Mapping

Ersetzen Sie technische Werte durch benutzerfreundliche Namen:

```json
{
  "display_map": {
    "application/pdf": "PDF-Dokument",
    "application/msword": "Word-Dokument",
    "text/html": "Webseite"
  }
}
```

### Nested Facetten

Für verschachtelte Strukturen (z.B. Konzept-Arrays):

```json
{
  "source": "nested",
  "nested_path": "concepts",
  "field": "concepts.label.keyword"
}
```

## Facetten verwalten

### Via Admin-UI

1. **Hinzufügen**: ➕ Button → Formular ausfüllen
2. **Bearbeiten**: ✏️ Button neben Facette
3. **Löschen**: 🗑️ Button (mit Bestätigung)
4. **Aktivieren/Deaktivieren**: Toggle-Switch
5. **Umsortieren**: Per Drag & Drop mit ☰ Handle

### Via API

**Alle Facetten abrufen:**
```bash
curl http://localhost:5000/admin/facets
```

**Neue Facette hinzufügen:**
```bash
curl -X POST http://localhost:5000/admin/facets \
  -H "Content-Type: application/json" \
  -d '{
    "id": "professions",
    "label": "Berufe",
    "field": "professions",
    "type": "terms",
    "icon": "👔",
    "size": 50
  }'
```

**Facette aktivieren/deaktivieren:**
```bash
curl -X POST http://localhost:5000/admin/facets/professions/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Facette löschen:**
```bash
curl -X DELETE http://localhost:5000/admin/facets/professions
```

**Reihenfolge ändern:**
```bash
curl -X POST http://localhost:5000/admin/facets/reorder \
  -H "Content-Type: application/json" \
  -d '{"facet_ids": ["professions", "document_type", "mime_type"]}'
```

## Persistenz

Die Facetten-Konfiguration wird in `/config/facets.json` gespeichert.

Um die Konfiguration zu sichern:

```bash
cp config/facets.json config/facets.backup.json
```

Um eine Konfiguration wiederherzustellen:

```bash
cp config/facets.backup.json config/facets.json
docker-compose restart search-api
```

## Troubleshooting

### Facette zeigt keine Werte

1. Prüfen Sie, ob das Feld im Index-Mapping existiert
2. Prüfen Sie, ob Dokumente dieses Feld enthalten
3. Überprüfen Sie die Browser-Konsole auf Fehler

### Ontologie wird nicht erkannt

1. Prüfen Sie, ob die Datei in `/ontologies` liegt
2. Prüfen Sie das Dateiformat (JSON/Turtle)
3. Prüfen Sie die Logs: `docker-compose logs indexer`

### Änderungen erscheinen nicht

1. Seite neu laden (F5)
2. Cache leeren (Strg+Shift+R)
3. API neu starten: `docker-compose restart search-api`

## Best Practices

1. **Weniger ist mehr**: Beginnen Sie mit 5-7 Facetten
2. **Aussagekräftige Labels**: "Berufe" statt "professions"
3. **Passende Icons**: Erleichtern die Navigation
4. **Sinnvolle Reihenfolge**: Wichtigste Facetten zuerst
5. **Größe anpassen**: `size: 50` für viele Werte, `size: 10` für wenige
6. **Testen**: Prüfen Sie die Facetten mit echten Daten

## Erweiterte Anwendungsfälle

### CV-Datenbank

Facetten für Lebenslauf-Suche:
- Berufe / Berufsbezeichnungen
- Skills / Programmiersprachen
- Erfahrungsjahre (Range)
- Ausbildung
- Standort
- Verfügbarkeit

### Produktkatalog

Facetten für E-Commerce:
- Kategorie
- Marke
- Preisspanne (Range)
- Farbe
- Größe
- Bewertung (Range)

### Dokumentenmanagement

Facetten für Unternehmensdokumente:
- Abteilung
- Projekt
- Dokumenttyp
- Autor
- Status (Draft/Review/Final)
- Vertraulichkeit

## Support

Bei Problemen:
1. Prüfen Sie die Logs: `docker-compose logs`
2. Prüfen Sie die API-Endpunkte im Browser
3. Öffnen Sie ein Issue auf GitHub
