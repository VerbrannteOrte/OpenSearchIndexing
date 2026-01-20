# ============================================================================
# Scripts/start.sh
# ============================================================================
#!/bin/bash
set -e

echo "=========================================="
echo "Starte OpenSearch Document Indexing"
echo "=========================================="
echo ""

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker ist nicht gestartet"
    echo "Bitte starten Sie Docker Desktop"
    exit 1
fi

# Services starten
docker-compose up -d

echo ""
echo "Services werden gestartet..."
sleep 5

echo ""
echo "=========================================="
echo "✓ Services gestartet!"
echo "=========================================="
echo ""
echo "Verfügbare Dienste:"
echo "  - OpenSearch:           http://localhost:9200"
echo "  - OpenSearch Dashboards: http://localhost:5601"
echo "  - Such-UI:              http://localhost:8080"
echo "  - Admin-UI (Facetten):  http://localhost:8080/admin.html"
echo "  - Admin-UI (Verz.):     http://localhost:8080/directories.html"
echo "  - API:                  http://localhost:5000"
echo ""
echo "Credentials:"
echo "  - Username: admin"
echo "  - Password: Admin123!"
echo ""
echo "Logs anzeigen:"
echo "  docker-compose logs -f"
echo ""
echo "Stoppen:"
echo "  ./Scripts/stop.sh"
echo ""
