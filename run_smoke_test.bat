@echo off
call venv\Scripts\activate

python mt5_test_simulator.py || (
    echo.
    echo [ERROR] Python script exited with error code %errorlevel%
)

call deactivate
pause