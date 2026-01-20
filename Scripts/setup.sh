#!/bin/bash
# Dies ist eine Sammlung aller Scripts
# Speichern Sie jedes Script einzeln im Scripts/ Verzeichnis

# ============================================================================
# Scripts/setup.sh
# ============================================================================
#!/bin/bash
set -e

echo "=========================================="
echo "OpenSearch Document Indexing - Setup"
echo "=========================================="
echo ""

# .env erstellen
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ .env erstellt"
    else
        cat > .env << 'ENV'
OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin123!
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=Admin123!
OCR_USE_GPU=false
OCR_ENABLE_SUETTERLIN=true
MAX_PAGES_PER_SITE=50
ENV
        echo "✓ .env erstellt (Standard)"
    fi
else
    echo "✓ .env bereits vorhanden"
fi

# Verzeichnisse erstellen
echo "Erstelle Daten-Verzeichnisse..."
mkdir -p Data/{documents,scans,watch,config,models,ontologies}
touch Data/documents/.gitkeep
touch Data/scans/.gitkeep
echo "✓ Verzeichnisse erstellt"

# Config-Dateien erstellen
if [ ! -f Data/config/facets.json ]; then
    if [ -f Config/facets.json.example ]; then
        cp Config/facets.json.example Data/config/facets.json
    else
        echo '{"facets":[],"version":"1.0"}' > Data/config/facets.json
    fi
    echo "✓ facets.json erstellt"
fi

if [ ! -f Data/config/indexing.json ]; then
    if [ -f Config/indexing.json.example ]; then
        cp Config/indexing.json.example Data/config/indexing.json
    else
        echo '{"directories":[],"version":"1.0"}' > Data/config/indexing.json
    fi
    echo "✓ indexing.json erstellt"
fi

# Ontologien kopieren
if [ -d Ontologies ]; then
    cp Ontologies/*.json Data/ontologies/ 2>/dev/null || true
    echo "✓ Ontologien kopiert"
fi

# Prüfe kritische Dateien
echo ""
echo "Prüfe erforderliche Dateien..."
MISSING=0

if [ ! -f docker-compose.yml ]; then
    echo "❌ FEHLT: docker-compose.yml"
    MISSING=1
fi

if [ ! -f Backend/indexer.py ]; then
    echo "❌ FEHLT: Backend/indexer.py"
    MISSING=1
fi

if [ ! -f Frontend/index.html ]; then
    echo "❌ FEHLT: Frontend/index.html"
    MISSING=1
fi

if [ ! -f requirements.txt ]; then
    echo "❌ FEHLT: requirements.txt"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "⚠️  FEHLER: Wichtige Dateien fehlen!"
    echo "Bitte kopieren Sie alle Artifacts aus Claude."
    echo "Siehe: Claude Artifacts-Sidebar (links)"
    exit 1
fi

echo "✓ Alle kritischen Dateien vorhanden"
echo ""

# Docker Images bauen
echo "Building Docker images..."
echo "Dies kann einige Minuten dauern..."
docker-compose build

echo ""
echo "=========================================="
echo "✓ Setup abgeschlossen!"
echo "=========================================="
echo ""
echo "Nächste Schritte:"
echo "  1. Prüfen Sie .env für Ihre Einstellungen"
echo "  2. Führen Sie aus: ./Scripts/start.sh"
echo "  3. Öffnen Sie: http://localhost:8080"
echo ""
