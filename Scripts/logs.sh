#!/bin/bash

SERVICE=${1:-""}

if [ -z "$SERVICE" ]; then
    echo "Zeige Logs aller Services (Ctrl+C zum Beenden):"
    docker-compose logs -f
else
    echo "Zeige Logs für Service: $SERVICE"
    docker-compose logs -f "$SERVICE"
fi
