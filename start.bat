@echo off
cd /d "%~dp0"
echo USJ 待ち時間モニター を起動しています...
start "USJ Collector" cmd /k python collector.py
start "USJ ngrok" cmd /k ngrok start --config ngrok.yml usj-dashboard
python -m streamlit run dashboard.py --server.address 0.0.0.0
