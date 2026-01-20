#!/bin/bash
set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "Backup erstellen"
echo "=========================================="
echo ""
echo "Backup-Verzeichnis: $BACKUP_DIR"
echo ""

# Config sichern
echo "Sichere Konfiguration..."
cp -r Data/config "$BACKUP_DIR/" 2>/dev/null || true

# Ontologien sichern
echo "Sichere Ontologien..."
cp -r Data/ontologies "$BACKUP_DIR/" 2>/dev/null || true

# .env sichern
echo "Sichere .env..."
cp .env "$BACKUP_DIR/" 2>/dev/null || true

# Index-Liste exportieren
echo "Exportiere Index-Liste..."
docker-compose exec -T opensearch curl -s -k -u admin:Admin123! \
  "https://localhost:9200/_cat/indices?v" > "$BACKUP_DIR/indices.txt" 2>/dev/null || true

echo ""
echo "✓ Backup erstellt in: $BACKUP_DIR"
echo ""
echo "Wiederherstellen:"
echo "  cp -r $BACKUP_DIR/config/* Data/config/"
echo "  cp -r $BACKUP_DIR/ontologies/* Data/ontologies/"
echo ""
