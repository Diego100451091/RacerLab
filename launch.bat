@echo off
title RacerLab - Instalador + Launcher
cd /d "%~dp0"

echo.
echo  ============================================
echo   RacerLab - Racing Lap Timer (G29)
echo  ============================================
echo.

:: Comprueba si existe entorno virtual local
if not exist ".venv\Scripts\python.exe" (
    echo  [*] Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo  [!] No se encontro Python. Instalalo desde https://python.org
        pause
        exit /b 1
    )
    echo  [*] Instalando dependencias...
    .venv\Scripts\pip install --quiet -r requirements.txt
    echo  [OK] Dependencias instaladas.
)

echo  [*] Iniciando RacerLab...
.venv\Scripts\python.exe lap_timer.py

if errorlevel 1 (
    echo.
    echo  [!] Error al ejecutar. Intentando instalar pygame de nuevo...
    .venv\Scripts\pip install pygame
    .venv\Scripts\python.exe lap_timer.py
)
