from flask import Flask, render_template, request, send_file, jsonify
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/om')
def om():
    return render_template('om.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/skapa')
def skapa():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    # Dummy exempel - här borde tabell byggas från formulärdata
    kontrollplan = [
        ["Kontrollpunkt", "Vem", "Metod", "Mot"],
        ["Utförandet överensstämmer med beviljat bygglov/startbesked", "BH", "Egenkontroll", "Startbesked"]
    ]
    return render_template('result.html', kontrollplan=kontrollplan)

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("Kontrollplan", styles['Heading1']))
    elements.append(Spacer(1,12))
    table = Table(data)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey),
                               ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                               ('ALIGN',(0,0),(-1,-1),'CENTER'),
                               ('GRID',(0,0),(-1,-1),1,colors.black)]))
    elements.append(table)
    elements.append(Spacer(1,24))
    elements.append(Paragraph("Härmed intygas att kontrollpunkterna har utförts och samtliga angivna krav har uppfyllts", styles['Normal']))
    elements.append(Spacer(1,24))
    elements.append(Paragraph("Datum: __________ Namnteckning: __________ Namnförtydligande: __________", styles['Normal']))
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="kontrollplan.pdf", mimetype="application/pdf")

@app.route('/health')
def health():
    return jsonify({"status":"ok"})

@app.route('/ping')
def ping():
    return "pong"

@app.route('/sitemap.xml')
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.kontrollplaner.com/</loc></url>
  <url><loc>https://www.kontrollplaner.com/om</loc></url>
  <url><loc>https://www.kontrollplaner.com/faq</loc></url>
  <url><loc>https://www.kontrollplaner.com/skapa</loc></url>
</urlset>'''
    return app.response_class(xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nAllow: /\nSitemap: https://www.kontrollplaner.com/sitemap.xml"

if __name__ == "__main__":
    app.run(debug=True)
