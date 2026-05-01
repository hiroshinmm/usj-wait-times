@echo off
cd /d "%~dp0"
echo USJ 待ち時間モニター を起動しています...
start "USJ Collector" cmd /k python collector.py
python -m streamlit run dashboard.py
