@echo off
setlocal enabledelayedexpansion

if "%1"=="" (
    call :show_help
    exit /b 1
)

set "command=%1"
set "command=%command: =%"

if /i "%command%"=="help" call :show_help
if /i "%command%"=="install" call :install
if /i "%command%"=="dev" call :install_dev
if /i "%command%"=="test" call :test
if /i "%command%"=="format" call :format
if /i "%command%"=="lint" call :lint
if /i "%command%"=="clean" call :clean
if /i "%command%"=="db-init" call :db_init
if /i "%command%"=="db-migrate" call :db_migrate
if /i "%command%"=="setup" call :setup
if /i "%command%"=="run" call :run
if /i "%command%"=="run-prod" call :run_prod
if /i "%command%"=="db-revision" (
    if "%2"=="" (
        echo Error: Message is required for db-revision command
        echo Usage: run.bat db-revision "description"
        exit /b 1
    )
    call :db_revision %2
)
goto :eof

:show_help
echo Boxcatering Chatbot - Available commands:
echo.
echo   help              Show this help message
echo   install           Install dependencies
echo   dev               Install development dependencies
echo   test              Run tests
echo   format            Format code with black and isort
echo   lint              Run linting checks
echo   clean             Clean up Python cache files
echo   db-init           Initialize database tables and create initial data
echo   db-migrate        Run database migrations
echo   db-revision       Create new migration ^(usage: run.bat db-revision "description"^)
echo   setup             Complete setup: init DB with data, run migrations
echo   run               Run the development server
echo   run-prod          Run the production server
echo.
echo Usage: run.bat ^<command^>
echo Example: run.bat install
goto :eof

:install
echo Installing dependencies...
uv pip install -e .
goto :eof

:install_dev
echo Installing development dependencies...
uv pip install -e ".[dev]"
goto :eof

:test
echo Running tests...
uv run pytest
goto :eof

:format
echo Formatting code with black and isort...
uv run black .
uv run isort .
goto :eof

:lint
echo Running linting checks...
uv run flake8 .
uv run mypy .
goto :eof

:clean
echo Cleaning up Python cache files...
for /r %%i in (*.pyc) do del "%%i" 2>nul
for /d /r %%i in (__pycache__) do rmdir /s /q "%%i" 2>nul
for /d /r %%i in (*.egg-info) do rmdir /s /q "%%i" 2>nul
goto :eof

:db_init
echo Initializing database tables and creating initial data...
uv run python scripts/init_db.py
goto :eof

:db_migrate
echo Running database migrations...
uv run alembic upgrade head
goto :eof

:db_revision
echo Creating new migration with message: %1
uv run alembic revision --autogenerate -m "%1"
goto :eof

:setup
echo Running complete setup...
call :db_init
call :db_migrate
goto :eof

:run
echo Starting development server...
uv run python start.py
goto :eof

:run_prod
echo Starting production server...
uv run python -m app.main
goto :eof
