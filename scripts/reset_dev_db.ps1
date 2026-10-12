<#
DEV ONLY: audit rows are immutable by design, so this is the only supported way to wipe a dev DB and must never be used on a real deployment.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "=====================================================================" -ForegroundColor Yellow
Write-Host " DEV ONLY: WIPE AND RESET DEV DATABASE" -ForegroundColor Yellow
Write-Host " Audit rows are immutable by design, so this is the only supported" -ForegroundColor Yellow
Write-Host " way to wipe a dev DB and must never be used on a real deployment." -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Yellow

$confirmation = Read-Host "Type 'RESET' to confirm destroying the postgres data volume"
if ($confirmation -ne "RESET") {
    Write-Host "Aborted. No changes made." -ForegroundColor Red
    exit 1
}

Write-Host "==> Deriving postgres data volume name from docker compose config..." -ForegroundColor Cyan
$composeConfig = docker compose config --format json | ConvertFrom-Json
$pgVolumeName = $composeConfig.volumes.pgdata.name

if (-not $pgVolumeName) {
    Write-Error "Could not derive pgdata volume name from docker compose config."
    exit 1
}

Write-Host "Derived postgres volume: $pgVolumeName" -ForegroundColor Green

Write-Host "==> Stopping docker compose stack (without removing volumes)..." -ForegroundColor Cyan
docker compose down

Write-Host "==> Removing ONLY the postgres data volume ($pgVolumeName)..." -ForegroundColor Cyan
# Never 'down -v', never touch ollama_data
docker volume rm $pgVolumeName

Write-Host "==> Restarting docker compose stack..." -ForegroundColor Cyan
docker compose up -d

Write-Host "==> Waiting for postgres container to become healthy..." -ForegroundColor Cyan
$retries = 30
while ($retries -gt 0) {
    $status = docker inspect --format '{{.State.Health.Status}}' clinical-scribe-postgres-1 2>$null
    if ($status -eq "healthy") {
        break
    }
    Start-Sleep -Seconds 2
    $retries--
}

Write-Host "==> Waiting for gateway container to become healthy..." -ForegroundColor Cyan
$retries = 30
while ($retries -gt 0) {
    $status = docker inspect --format '{{.State.Health.Status}}' clinical-scribe-gateway-1 2>$null
    if ($status -eq "healthy") {
        break
    }
    Start-Sleep -Seconds 2
    $retries--
}

Write-Host "==> Running Alembic migrations on clinical_scribe (dev DB)..." -ForegroundColor Cyan
if (-not $env:POSTGRES_SUPERUSER_PASSWORD -and (Test-Path .env)) {
    Get-Content .env | Where-Object { $_ -match '^POSTGRES_SUPERUSER_PASSWORD=(.*)$' } | ForEach-Object {
        $env:POSTGRES_SUPERUSER_PASSWORD = $Matches[1].Trim()
    }
}
$superuser_pw = if ($env:POSTGRES_SUPERUSER_PASSWORD) { $env:POSTGRES_SUPERUSER_PASSWORD } else { "" }
docker compose exec -T -e POSTGRES_SUPERUSER=postgres -e POSTGRES_SUPERUSER_PASSWORD=$superuser_pw -e POSTGRES_DB=clinical_scribe gateway alembic -c /app/alembic.ini upgrade head

Write-Host "==> Dev database has been successfully reset, migrated, and seeded." -ForegroundColor Green
