@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Checking Python 3.14 virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python 3.14 virtual environment...
    py -3.14 -m venv .venv
    if errorlevel 1 (
        echo Python 3.14 was not found. Please install Python 3.14 first.
        pause
        exit /b 1
    )
)

echo [2/4] Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo [3/4] Starting Stock AI Pro server...
start "Stock AI Pro Server" /min cmd /c "cd /d ""%~dp0"" && "".venv\Scripts\python.exe"" -m streamlit run app.py --server.headless true"

echo Waiting for the web server to start...
timeout /t 4 /nobreak >nul

echo [4/4] Opening Stock AI Pro in your default browser...
start "" "http://localhost:8501"

echo.
echo Stock AI Pro is running at http://localhost:8501
 echo Close the server window to stop the application.
endlocal
exit /b 0
