
# Kontrollplaner.com – Komplett projekt med GA4

- Flask-app med landningssida, Om, FAQ, Privacy, Terms
- Kontrollplan-generator för privatpersoner (8 åtgärder)
- Redigera/radera/lägg till rader + låsta obligatoriska rader
- PDF i liggande A4 med intygsrad och legend
- SEO: canonical, OG/Twitter, sitemap/robots
- Health: /health, /ping
- GA4: templates/_ga.html (G-FP97MP64VT) + events
  - uppgifter_skickade (index)
  - kontrollplan_skapad (result)
  - pdf_nedladdad (result/script.js)

## Lokalt
pip install -r requirements.txt
python app.py

## Render
git add -A
git commit -m "Fullt projekt med GA4 events"
git push origin main
