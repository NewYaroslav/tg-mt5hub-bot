@echo off
call venv\Scripts\activate

python mt5hub_bot.py || (
    echo.
    echo [ERROR] Python script exited with error code %errorlevel%
)

call deactivate
pause