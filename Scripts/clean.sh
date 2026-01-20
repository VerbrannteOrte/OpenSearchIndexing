#!/bin/bash

echo "=========================================="
echo "Cleanup"
echo "=========================================="
echo ""

read -p "Stoppen und entfernen aller Container? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose down
    echo "✓ Container gestoppt und entfernt"
fi

echo ""
read -p "Docker Images entfernen? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose down --rmi all
    echo "✓ Images entfernt"
fi

echo ""
read -p "Volumes entfernen (ACHTUNG: Löscht alle Daten!)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose down -v
    echo "✓ Volumes entfernt"
    echo "⚠️  Alle Daten wurden gelöscht!"
fi

echo ""
echo "Cleanup abgeschlossen"

