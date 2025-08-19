from flask import Flask, render_template, request, send_file, make_response
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

app = Flask(__name__)

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/skapa")
def skapa():
    return render_template("index.html")

@app.route("/result", methods=["POST"])
def result():
    namn = request.form.get("namn")
    adress = request.form.get("adress")
    fastighet = request.form.get("fastighet")
    projektbeskrivning = request.form.get("projektbeskrivning")

    kontrollplan = [
        ["Kontrollpunkt", "Vem (BH/KA/E)", "Metod"],
        ["Utförandet överensstämmer med bygglov/startbesked", "BH", "Egenkontroll"],
        ["Bärande konstruktioner", "E", "Kontroll mot handlingar"],
        ["Fuktskydd", "E", "Egenkontroll, foton"],
        ["Brandskydd (brandvarnare, släckare)", "BH", "Egenkontroll"],
        ["Energikrav & täthet", "E", "Mätning & intyg"]
    ]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Byggherre:</b> {namn}", styles['Normal']))
    story.append(Paragraph(f"<b>Adress:</b> {adress}", styles['Normal']))
    story.append(Paragraph(f"<b>Fastighetsbeteckning:</b> {fastighet}", styles['Normal']))
    story.append(Paragraph(f"<b>Projektbeskrivning:</b> {projektbeskrivning}", styles['Normal']))
    story.append(Spacer(1, 12))

    table = Table(kontrollplan, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER")
    ]))
    story.append(table)
    story.append(Spacer(1, 24))

    story.append(Paragraph("Härmed intygas att kontrollpunkterna har utförts och samtliga angivna krav har uppfyllts", styles['Normal']))
    story.append(Spacer(1, 36))
    story.append(Paragraph("Datum: ____________________", styles['Normal']))
    story.append(Paragraph("Namnteckning: ____________________", styles['Normal']))
    story.append(Paragraph("Namnförtydligande: ____________________", styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="kontrollplan.pdf")

@app.route("/om")
def om():
    return render_template("om.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/robots.txt")
def robots():
    resp = make_response("User-agent: *\nAllow: /\nSitemap: https://www.kontrollplaner.com/sitemap.xml")
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/sitemap.xml")
def sitemap():
    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://www.kontrollplaner.com/</loc></url>
      <url><loc>https://www.kontrollplaner.com/skapa</loc></url>
      <url><loc>https://www.kontrollplaner.com/om</loc></url>
      <url><loc>https://www.kontrollplaner.com/faq</loc></url>
    </urlset>'''
    resp = make_response(sitemap_xml)
    resp.headers["Content-Type"] = "application/xml"
    return resp

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(debug=True)
