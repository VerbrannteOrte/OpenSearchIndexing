#!/bin/bash
set -e

echo "Neustarten der Services..."
docker-compose restart

echo ""
echo "✓ Services wurden neugestartet"
echo ""
