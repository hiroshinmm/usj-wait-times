@echo off
cd /d "%~dp0"
echo USJ 待ち時間モニター を起動しています...
start "USJ Collector" cmd /k python collector.py
start "USJ Tunnel" cmd /k python tunnel.py
python -m streamlit run dashboard.py --server.address 0.0.0.0
