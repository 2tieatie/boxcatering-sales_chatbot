#!/usr/bin/env pwsh

param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Boxcatering Chatbot - Available commands:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  help              Show this help message" -ForegroundColor Green
    Write-Host "  install           Install dependencies" -ForegroundColor Green
    Write-Host "  dev               Install development dependencies" -ForegroundColor Green
    Write-Host "  test              Run tests" -ForegroundColor Green
    Write-Host "  format            Format code with black and isort" -ForegroundColor Green
    Write-Host "  lint              Run linting checks" -ForegroundColor Green
    Write-Host "  clean             Clean up Python cache files" -ForegroundColor Green
    Write-Host "  db-init           Initialize database tables and create initial data" -ForegroundColor Green
    Write-Host "  db-migrate        Run database migrations" -ForegroundColor Green
    Write-Host "  db-revision       Create new migration (usage: .\run.ps1 db-revision -msg 'description')" -ForegroundColor Green
    Write-Host "  setup             Complete setup: init DB with data, run migrations" -ForegroundColor Green
    Write-Host "  run               Run the development server" -ForegroundColor Green
    Write-Host "  run-prod          Run the production server" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\run.ps1 <command>" -ForegroundColor Yellow
    Write-Host "Example: .\run.ps1 install" -ForegroundColor Yellow
}

function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    uv pip install -e .
}

function Install-DevDependencies {
    Write-Host "Installing development dependencies..." -ForegroundColor Yellow
    uv pip install -e ".[dev]"
}

function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Yellow
    uv run pytest
}

function Format-Code {
    Write-Host "Formatting code with black and isort..." -ForegroundColor Yellow
    uv run black .
    uv run isort .
}

function Run-Linting {
    Write-Host "Running linting checks..." -ForegroundColor Yellow
    uv run flake8 .
    uv run mypy .
}

function Clean-Cache {
    Write-Host "Cleaning up Python cache files..." -ForegroundColor Yellow
    Get-ChildItem -Recurse -Include "*.pyc" | Remove-Item -Force
    Get-ChildItem -Recurse -Directory -Name "__pycache__" | ForEach-Object { Remove-Item -Recurse -Force $_ }
    Get-ChildItem -Recurse -Directory -Include "*.egg-info" | Remove-Item -Recurse -Force
}

function Initialize-Database {
    Write-Host "Initializing database tables and creating initial data..." -ForegroundColor Yellow
    uv run python scripts/init_db.py
}

function Run-Migrations {
    Write-Host "Running database migrations..." -ForegroundColor Yellow
    uv run alembic upgrade head
}

function Create-Revision {
    param([string]$msg)
    if (-not $msg) {
        Write-Host "Error: Message is required for db-revision command" -ForegroundColor Red
        Write-Host "Usage: .\run.ps1 db-revision -msg 'description'" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Creating new migration with message: $msg" -ForegroundColor Yellow
    uv run alembic revision --autogenerate -m $msg
}

function Complete-Setup {
    Write-Host "Running complete setup..." -ForegroundColor Yellow
    Initialize-Database
    Run-Migrations
}

function Run-DevServer {
    Write-Host "Starting development server..." -ForegroundColor Yellow
    uv run python start.py
}

function Run-ProdServer {
    Write-Host "Starting production server..." -ForegroundColor Yellow
    uv run python -m app.main
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "dev" { Install-DevDependencies }
    "test" { Run-Tests }
    "format" { Format-Code }
    "lint" { Run-Linting }
    "clean" { Clean-Cache }
    "db-init" { Initialize-Database }
    "db-migrate" { Run-Migrations }
    "db-revision" { 
        $msg = $args[0]
        Create-Revision -msg $msg 
    }
    "setup" { Complete-Setup }
    "run" { Run-DevServer }
    "run-prod" { Run-ProdServer }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
