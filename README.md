services:
  - type: web
    name: nasdaq-watchdog
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python stock-movers-bot.py
