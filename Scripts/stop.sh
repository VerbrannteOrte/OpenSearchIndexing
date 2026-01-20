# ============================================================================
# Scripts/stop.sh
# ============================================================================
#!/bin/bash

echo "Stoppe Services..."
docker-compose down

echo ""
echo "✓ Alle Services gestoppt"
echo ""
echo "Daten bleiben erhalten in:"
echo "  - Docker Volume: opensearch-data"
echo "  - Lokale Daten: ./Data/"
echo ""
echo "Neu starten:"
echo "  ./Scripts/start.sh"
echo ""
