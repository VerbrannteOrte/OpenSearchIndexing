#!/bin/bash
set -e

echo "=========================================="
echo "Update"
echo "=========================================="
echo ""

echo "Stoppe Services..."
docker-compose down

echo "Rebuild Images..."
docker-compose build --no-cache

echo "Starte Services..."
docker-compose up -d

echo ""
echo "✓ Update abgeschlossen"
echo ""

