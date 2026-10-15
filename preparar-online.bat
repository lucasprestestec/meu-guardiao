@echo off
rem Duplo clique: prepara o banco e os dados de exemplo da demonstracao online.
cd /d "%~dp0"
where python >nul 2>nul && (python db\preparar_online.py & goto fim)
where py >nul 2>nul && (py db\preparar_online.py & goto fim)
if exist "%LOCALAPPDATA%\Programs\Python\Python39\python.exe" (
  "%LOCALAPPDATA%\Programs\Python\Python39\python.exe" db\preparar_online.py & goto fim
)
echo Python nao encontrado. Instale em python.org (marque "Add python.exe to PATH").
:fim
echo.
pause
