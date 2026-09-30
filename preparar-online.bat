@echo off
rem Duplo clique: prepara o banco e os dados de exemplo da demonstração online.
cd /d "%~dp0"
python db\preparar_online.py
echo.
pause
