<#
.SYNOPSIS
    Recreates clinical_scribe_test database, runs migrations, and runs pytest against it.
.DESCRIPTION
    Ensures absolute test database isolation so tests never pollute or read from the dev database.
    Accepts arbitrary arguments passed to pytest (e.g. .\scripts\test_gateway.ps1 tests/gateway/ -v).
#>

[CmdletBinding()]
param (
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"

Write-Host "==> Resetting clinical_scribe_test database..." -ForegroundColor Cyan

# Terminate active connections and recreate the test database
docker compose exec -T postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'clinical_scribe_test' AND pid <> pg_backend_pid();" | Out-Null
docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS clinical_scribe_test;" | Out-Null
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE clinical_scribe_test;" | Out-Null
docker compose exec -T postgres psql -U postgres -c "GRANT CONNECT ON DATABASE clinical_scribe_test TO scribe_app;" | Out-Null

Write-Host "==> Running migrations and seeds on clinical_scribe_test..." -ForegroundColor Cyan
if (-not $env:POSTGRES_SUPERUSER_PASSWORD -and (Test-Path .env)) {
    Get-Content .env | Where-Object { $_ -match '^POSTGRES_SUPERUSER_PASSWORD=(.*)$' } | ForEach-Object {
        $env:POSTGRES_SUPERUSER_PASSWORD = $Matches[1].Trim()
    }
}
$superuser_pw = if ($env:POSTGRES_SUPERUSER_PASSWORD) { $env:POSTGRES_SUPERUSER_PASSWORD } else { "" }
docker compose exec -T -e POSTGRES_SUPERUSER=postgres -e POSTGRES_SUPERUSER_PASSWORD=$superuser_pw -e POSTGRES_DB=clinical_scribe_test gateway alembic -c /app/alembic.ini upgrade head

Write-Host "==> Executing pytest against clinical_scribe_test..." -ForegroundColor Cyan
if (-not $PytestArgs -or $PytestArgs.Count -eq 0) {
    $PytestArgs = @("tests/gateway/", "-v")
}

# Separate, long TEST key (distinct from dev and prod, > 32 bytes)
$TestJwtSecret = "clinical_scribe_test_secret_key_distinct_from_dev_and_prod_environment_length_64_bytes_ok"
$cmd = @("exec", "-T", "-e", "PYTHONPATH=/app", "-e", "POSTGRES_DB=clinical_scribe_test", "-e", "JWT_SECRET=$TestJwtSecret", "gateway", "pytest") + $PytestArgs
& docker compose $cmd

exit $LASTEXITCODE
