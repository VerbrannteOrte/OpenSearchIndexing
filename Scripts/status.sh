#!/bin/bash

echo "=========================================="
echo "Service Status"
echo "=========================================="
echo ""

docker compose ps

echo ""
echo "Disk Usage:"
docker system df

echo ""
echo "Volumes:"
docker volume ls | grep opensearch
