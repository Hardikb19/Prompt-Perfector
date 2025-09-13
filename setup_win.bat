@echo off
REM Setup script for Prompt Perfector on Windows

python -m venv venv
call venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python -m promptperfector.logic

echo Setup complete. To run: call venv\Scripts\activate && python -m promptperfector.main
