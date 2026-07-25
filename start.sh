#!/bin/bash
echo "Starting Loukarver Backend with Docker..."
docker compose up --build -d
echo "Backend should be running at http://localhost:8000"
