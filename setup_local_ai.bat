@echo off
setlocal
cd /d "%~dp0"
echo =============================================
echo Stock AI Pro - Local AI setup
 echo =============================================
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama is not installed.
  echo Install it from https://ollama.com/download/windows
  start "" "https://ollama.com/download/windows"
  pause
  exit /b 1
)

echo Pulling local model: qwen3.5:4b
ollama pull qwen3.5:4b
if errorlevel 1 (
  echo Model download failed.
  pause
  exit /b 1
)

echo Local AI is ready.
echo You can now run run_stock_ai.bat
pause
