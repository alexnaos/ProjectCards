@echo off
:: Project Cards - Scheduled Execution Script
:: Можно добавить в Windows Task Scheduler или использовать cron

cd /d "c:\Projects\ProjectCards"

:: Activate virtual environment (if exists)
if exist venv (
    call venv\Scripts\activate
)

:: Set environment variables
set PYTHONPATH=.

:: Run project cards generation
echo Starting project cards generation...
python create_cards.py

if %errorlevel% equ 0 (
    echo Project cards generation completed successfully.
) else (
    echo Project cards generation completed with errors.
)

echo Done.