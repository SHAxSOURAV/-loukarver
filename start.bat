@echo off
echo Starting Samesy Backend with Docker...
docker compose up --build
echo.
echo Backend should be running at http://localhost:8000
pause
