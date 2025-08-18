
# Kontrollplaner – Flask-app

## Kör lokalt
```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
```

## Deploy på Render
- Pusha denna mapp till GitHub.
- Render: New → Web Service → Build from GitHub.
- Render läser `render.yaml` och kör:
  - Build: `pip install -r requirements.txt`
  - Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Lägg ev. env vars:
  - `GA_ID` (ex G-XXXXXXXXXX)
  - `MATOMO_URL` (ex https://matomo.dindomän.se/)
  - `MATOMO_SITE_ID` (ex 1)
- Testa `/health`.

## Struktur
- `app.py` – Flask, PDF, routes, cookie.js templating
- `templates/` – sidorna
- `static/` – css & js
- `render.yaml` / `Procfile` / `requirements.txt`
