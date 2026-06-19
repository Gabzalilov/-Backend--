$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker не найден. Установите Docker Desktop и повторите запуск."
}

Write-Host "Запускаю Ollama, загружаю DeepSeek и собираю backend..." -ForegroundColor Cyan
Write-Host "Первый запуск может занять несколько минут: модель скачивается один раз." -ForegroundColor Yellow

docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose завершился с ошибкой. Выполните: docker compose logs"
}

Write-Host ""
Write-Host "Сервисы запущены:" -ForegroundColor Green
docker compose ps
Write-Host ""
Write-Host "Лендинг: http://127.0.0.1:8000"
Write-Host "Swagger:  http://127.0.0.1:8000/docs"
Write-Host "Проверка: http://127.0.0.1:8000/api/health"

