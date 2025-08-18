
# Kontrollplan-app (Flask) – Render deploy

## Kör lokalt
```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
```

## Struktur
- app.py (Flask, PDF med ReportLab, /health)
- templates/ (index.html, result.html)
- static/ (style.css, script.js)
- requirements.txt
- Procfile
- render.yaml
- README.md

## Deploy till Render (gratisplan)
1. Skapa ett nytt repo på GitHub och pusha denna mapp.
2. Gå till https://render.com → New → **Web Service** → **Build and deploy from a Git repository**.
3. Välj repot. Render läser `render.yaml` och använder:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. När deploy är klar får du en publik URL. Testa `/health`:
   `https://dinapp.onrender.com/health` → `{"ok": true}`

## Egen domän
- Render-projekt → Settings → **Custom Domains** → lägg till din domän → följ DNS-guiden.
