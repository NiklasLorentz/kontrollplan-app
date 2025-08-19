
import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, send_file, Response
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape

app = Flask(__name__)

# ---------- Health ----------
@app.route("/health")
def health():
    return {"ok": True}, 200

@app.route("/ping")
def ping():
    return "pong", 200

# ---------- Pages ----------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/om")
def om():
    return render_template("om.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/skapa", methods=["GET","POST"])
def skapa():
    fields = [
        "bygglovstyp","byggherre","telefon","epost",
        "fastighetsbeteckning","fastighetsadress",
        "ka_namn","ka_kontakt","projektbeskrivning"
    ]
    data = {k: "" for k in fields}
    src = request.form if request.method=='POST' and request.form else request.args
    for k in fields:
        data[k] = (src.get(k,"") if src else "")
    typer = [
        "Nybyggnad (villa/småhus)",
        "Tillbyggnad",
        "Fasadändring",
        "Takomläggning",
        "Garage / Komplementbyggnad",
        "Altan / Uterum",
        "Pool",
        "Attefallsåtgärder"
    ]
    return render_template("index.html", typer=typer, data=data)

@app.route("/result", methods=["POST"])
def result():
    form = {k: request.form.get(k, "") for k in [
        "bygglovstyp","byggherre","telefon","epost",
        "fastighetsbeteckning","fastighetsadress",
        "ka_namn","ka_kontakt","projektbeskrivning"
    ]}
    rows = plan_rows(form.get("bygglovstyp",""))
    return render_template("result.html", rows=rows, **form)

# ---------- Kontrollplansdata (fokus privatpersoner) ----------
def plan_rows(bygglovstyp: str):
    t = (bygglovstyp or "").lower()

    def cat(name):
        return {"is_category": True, "kategori": name, "obligatorisk": False}

    def row(kp, vem, hur, mot, nar="Under arbetet", sign="", oblig=False):
        return {
            "is_category": False,
            "kontrollpunkt": kp,
            "vem": vem,     # BH / KA / E
            "hur": hur,     # metod
            "mot": mot,     # kontroll mot
            "nar": nar,     # när
            "signatur": sign,
            "obligatorisk": oblig,
        }

    # ---- Nybyggnad (villa/småhus) ----
    if "nybygg" in t:
        return [
            cat("Mark och grund"),
            row("Utsättning av byggnad på tomten", "BH", "Kontrollmätning", "Situationsplan, bygglovsbeslut", "Före byggstart", oblig=True),
            row("Markarbete och schakt", "E", "Visuell kontroll / foto", "Ritningar, PBL"),
            row("Grundläggning, dränering och fuktskydd", "E", "Egenkontroll, foto", "BBR, AMA"),
            cat("Stomme och klimatskal"),
            row("Bärande stomme (väggar, bjälklag)", "E", "Egenkontroll, foto", "Konstruktionsritningar"),
            row("Takstolar och yttertak", "E", "Egenkontroll, foto", "Ritningar"),
            row("Ytterväggar inkl. isolering & ång-/vindskydd", "E", "Egenkontroll, foto", "BBR"),
            row("Fönster och dörrar (placering, tätning)", "E", "Egenkontroll", "Ritningar, BBR"),
            cat("Installationer"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS (vatten/avlopp)", "E", "Täthetsprov, intyg", "Säker Vatten / branschregler"),
            row("Ventilation", "E", "Injustering, funktionsprov", "BBR"),
            row("Brandskydd i bostaden (brandvarnare, släckare, brandfilt)", "BH", "Egenkontroll", "BBR, MSB rekommendationer"),
            row("Energikrav (täthet/isolering)", "E", "Provtryckning, intyg", "BBR", "Före slutsamråd"),
            cat("Slutkontroll"),
            row("Utförandet överensstämmer med beviljat bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Innan slutbesked", oblig=True),
        ]

    # ---- Tillbyggnad ----
    if "tillbygg" in t:
        return [
            cat("Mark och grund"),
            row("Utsättning av tillbyggnad", "BH", "Kontrollmätning", "Situationsplan, bygglovsbeslut", "Före byggstart", oblig=True),
            row("Markarbete och grundläggning", "E", "Egenkontroll, foto", "Ritningar, BBR"),
            cat("Stomme och klimatskal"),
            row("Bärande stomme", "E", "Egenkontroll, foto", "Konstruktionsritningar"),
            row("Yttertak (anslutning mot befintligt)", "E", "Egenkontroll, foto", "Ritningar"),
            row("Ytterväggar inkl. isolering & fuktskydd", "E", "Egenkontroll", "BBR"),
            row("Anslutning mot befintlig byggnad (täthet, fuktskydd)", "E", "Egenkontroll, foto", "BBR"),
            cat("Installationer (om aktuellt)"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer", "E", "Intyg", "Branschregler"),
            row("Brandskydd i bostaden (brandvarnare/släckare)", "BH", "Egenkontroll", "BBR, MSB"),
            cat("Slutkontroll"),
            row("Utförandet överensstämmer med bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Innan slutbesked", oblig=True),
        ]

    # ---- Fasadändring ----
    if "fasad" in t:
        return [
            cat("Fasadåtgärd"),
            row("Åtgärden stämmer med bygglov/startbesked", "BH", "Visuell kontroll", "Bygglovsbeslut, startbesked", "Före arbetet", oblig=True),
            row("Rivning av befintlig fasaddel (om aktuellt)", "E", "Foto, egenkontroll", "Ritningar"),
            row("Ny fasadbeklädnad (material, infästningar)", "E", "Egenkontroll, foto", "Ritningar, BBR"),
            row("Färgsättning enligt handling", "BH", "Visuell kontroll", "Bygglovsbeslut"),
            row("Fönster/dörrar (utförande, placering, kulör)", "E", "Egenkontroll", "Ritningar, BBR"),
            row("Tätning och fuktskydd (skarvar, anslutningar)", "E", "Egenkontroll, foto", "BBR"),
            cat("Slutkontroll"),
            row("Utförandet överensstämmer med bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Efter arbetet", oblig=True),
        ]

    # ---- Takomläggning ----
    if "tak" in t:
        return [
            cat("Rivning och underlag"),
            row("Rivning av befintligt yttertak", "E", "Egenkontroll, foto", "Ritningar"),
            row("Underlagspapp/duk monterad korrekt", "E", "Egenkontroll", "Tillverkarens anvisningar"),
            cat("Nytt tak"),
            row("Takbeläggning (pannor/plåt) korrekt lagd", "E", "Egenkontroll", "BBR / anvisningar"),
            row("Takavvattning (rännor/stuprör)", "E", "Egenkontroll", "Ritningar"),
            row("Taksäkerhet (steg, glidskydd, gångbryggor)", "E", "Egenkontroll", "Föreskrifter"),
            cat("Slutkontroll"),
            row("Åtgärden stämmer med handling/startbesked", "BH", "Granskning, egenkontroll", "Startbesked", "Efter arbetet", oblig=True),
        ]

    # ---- Garage / Komplementbyggnad ----
    if "garage" in t or "komplement" in t:
        return [
            cat("Läge och grund"),
            row("Placering enligt situationsplan", "BH", "Kontrollmätning", "Situationsplan, startbesked", "Före byggstart", oblig=True),
            row("Grundläggning (platta/plintar)", "E", "Egenkontroll, foto", "Ritningar"),
            cat("Stomme och klimatskal"),
            row("Bärande stomme", "E", "Egenkontroll", "Ritningar"),
            row("Tak och väggar", "E", "Egenkontroll", "Ritningar"),
            row("Portar/dörrar/fönster", "E", "Egenkontroll", "Ritningar"),
            cat("Installationer (om aktuellt)"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("Dagvatten/avrinnning", "E", "Visuell kontroll", "Kommunens krav"),
            cat("Slutkontroll"),
            row("Utförandet överensstämmer med startbesked", "BH", "Granskning, intyg", "Startbesked", "Efter arbetet", oblig=True),
        ]

    # ---- Altan / Uterum ----
    if "altan" in t or "uterum" in t:
        return [
            cat("Placering och grund"),
            row("Placering enligt handling (höjd/utbredning)", "BH", "Mätning / visuell", "Situationsplan", "Före byggstart", oblig=True),
            row("Grundläggning/infästningar", "E", "Egenkontroll, foto", "Ritningar"),
            cat("Byggnation"),
            row("Stomme och räcken (skydd mot fall)", "E", "Egenkontroll", "BBR"),
            row("Uterum – glaspartier och tak (om aktuellt)", "E", "Egenkontroll", "Ritningar"),
            row("Dagvattenavrinning", "E", "Visuell kontroll", "Kommunens krav"),
            cat("Slutkontroll"),
            row("Åtgärden stämmer med startbesked", "BH", "Granskning", "Startbesked", "Efter arbetet", oblig=True),
        ]

    # ---- Pool ----
    if "pool" in t:
        return [
            cat("Mark och grund"),
            row("Schakt och dränering", "E", "Egenkontroll, foto", "Ritningar"),
            row("Platta/skål och täthet", "E", "Egenkontroll, tryckprov", "Tillverkarens anvisningar"),
            cat("Säkerhet"),
            row("Skydd mot olyckor (skydd/staket/larm)", "BH", "Egenkontroll", "Boverkets råd"),
            cat("Teknik"),
            row("Elinstallationer (pumpar/belysning)", "E", "Intyg", "Elsäkerhetslagen"),
            row("Vattenbehandling/anslutningar", "E", "Egenkontroll", "Leverantörens anvisningar"),
            cat("Slutkontroll"),
            row("Åtgärden stämmer med eventuellt startbesked", "BH", "Granskning", "Startbesked/handling", "Efter arbetet", oblig=True),
        ]

    # ---- Attefallsåtgärder ----
    if "attefall" in t:
        return [
            cat("Läge och mått"),
            row("Placering på tomten enligt situationsplan", "BH", "Kontrollmätning", "Situationsplan, ev. startbesked", "Före byggstart", oblig=True),
            row("Mått (höjd/area) inom attefallsregler", "BH", "Kontrollmätning", "PBL/PBF", "Före byggstart", oblig=True),
            cat("Byggnation"),
            row("Grundläggning (plintar/platta) med fuktskydd", "E", "Egenkontroll, foto", "Ritningar, BBR"),
            row("Bärande stomme", "E", "Egenkontroll", "Ritningar"),
            row("Tak och tätskikt", "E", "Egenkontroll", "Ritningar"),
            row("Fasadbeklädnad och färgsättning", "BH", "Visuell kontroll", "Handling/startbesked"),
            row("Fönster/dörrar – infästning/tätning", "E", "Egenkontroll", "Ritningar, BBR"),
            cat("Installationer (om aktuellt)"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer", "E", "Intyg", "Branschregler"),
            row("Brandskydd i bostaden (brandvarnare/släckare)", "BH", "Egenkontroll", "BBR, MSB"),
            cat("Slutkontroll"),
            row("Utförandet överensstämmer med startbesked", "BH", "Granskning, intyg", "Startbesked/anmälan", "Efter arbetet", oblig=True),
        ]

    # Fallback
    return [cat("Rubrik"), row("Ny kontrollpunkt", "BH", "Egenkontroll", "Ritningar")]

# ---------- PDF ----------
@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    form = {k: request.form.get(k, "") for k in [
        "bygglovstyp","byggherre","telefon","epost",
        "fastighetsbeteckning","fastighetsadress",
        "ka_namn","ka_kontakt","projektbeskrivning"
    ]}

    kategorier = request.form.getlist("kategori[]")
    is_category = request.form.getlist("is_category[]")
    kp  = request.form.getlist("kp[]")
    vem = request.form.getlist("vem[]")
    hur = request.form.getlist("hur[]")
    mot = request.form.getlist("mot[]")
    nar = request.form.getlist("nar[]")
    sign = request.form.getlist("signatur[]")

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=10)
    head = ParagraphStyle('head', parent=styles['Heading1'], fontSize=16, leading=18, spaceAfter=6)

    def P(x, st=small):
        return Paragraph(escape(x or ""), st)

    story = []
    story.append(Paragraph(f"Kontrollplan – {escape(form['bygglovstyp'])}", head))

    info = [
        ["Byggherre:", f"{form['byggherre']}"],
        ["Telefon:", f"{form['telefon']}"],
        ["E‑post:", f"{form['epost']}"],
        ["Fastighetsbeteckning:", f"{form['fastighetsbeteckning']}"],
        ["Fastighetsadress:", f"{form['fastighetsadress']}"],
        ["Kontrollansvarig:", f"{form['ka_namn']} {form['ka_kontakt']}"],
        ["Projektbeskrivning:", f"{form['projektbeskrivning']}"],
    ]
    info_table = Table(info, colWidths=[120, 620])
    info_table.setStyle(TableStyle([
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('BOTTOMPADDING',(0,0),(-1,-1),4)
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    headers = ["Kategori/Kontrollpunkt","Vem","Hur","Kontroll mot","När","Signatur / Datum"]
    data = [[Paragraph(f"<b>{h}</b>", small) for h in headers]]
    category_rows = []
    idx_cat = 0
    idx_data = 0
    for flag in is_category:
        if flag == "1":
            title = kategorier[idx_cat] if idx_cat < len(kategorier) else ""
            data.append([P(title), "", "", "", "", ""])
            category_rows.append(len(data)-1)
            idx_cat += 1
        else:
            c_kp   = kp[idx_data]   if idx_data < len(kp)   else ""
            c_vem  = vem[idx_data]  if idx_data < len(vem)  else ""
            c_hur  = hur[idx_data]  if idx_data < len(hur)  else ""
            c_mot  = mot[idx_data]  if idx_data < len(mot)  else ""
            c_nar  = nar[idx_data]  if idx_data < len(nar)  else ""
            c_sign = sign[idx_data] if idx_data < len(sign) else ""
            data.append([P(c_kp), P(c_vem), P(c_hur), P(c_mot), P(c_nar), P(c_sign)])
            idx_data += 1

    table = Table(data, repeatRows=1, colWidths=[250, 60, 150, 150, 80, 100])
    style = TableStyle([
        ('BACKGROUND',(0,0),(-1,0),'#eef2f7'),
        ('GRID',(0,0),(-1,-1),0.5,colors.black),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('FONTSIZE',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),4),
        ('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4)
    ])
    for r in category_rows:
        style.add('SPAN',(0,r),(-1,r))
        style.add('BACKGROUND',(0,r),(-1,r),'#e8f1ff')
        style.add('FONTNAME',(0,r),(-1,r),'Helvetica-Bold')
    table.setStyle(style)
    story.append(table)

    story.append(Spacer(1,12))
    story.append(P("Härmed intygas att kontrollpunkterna har utförts och samtliga angivna krav har uppfyllts"))
    story.append(Spacer(1,10))
    story.append(P("Datum: __________________________  Namnteckning: __________________________  Namnförtydligande: __________________________"))
    story.append(Spacer(1,12))
    story.append(P("Förkortningar: BH = Byggherre • KA = Kontrollansvarig • E = Entreprenör"))

    doc.build(story)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="kontrollplan.pdf", mimetype="application/pdf")

# ---------- SEO ----------
@app.route("/sitemap.xml")
def sitemap_xml():
    host = request.host or "www.kontrollplaner.com"
    base = f"https://{host}"
    today = datetime.now(timezone.utc).date().isoformat()
    pages = [
        {"loc": base + "/", "changefreq": "weekly", "priority": "1.0"},
        {"loc": base + "/skapa", "changefreq": "weekly", "priority": "0.9"},
        {"loc": base + "/om", "changefreq": "monthly", "priority": "0.6"},
        {"loc": base + "/faq", "changefreq": "monthly", "priority": "0.6"},
    ]
    xml_items = []
    for p in pages:
        xml_items.append(f"""  <url>
    <loc>{p['loc']}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{p['changefreq']}</changefreq>
    <priority>{p['priority']}</priority>
  </url>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(xml_items)}
</urlset>
"""
    return Response(xml, mimetype="application/xml")

@app.route("/robots.txt")
def robots_txt():
    host = request.host or "www.kontrollplaner.com"
    base = f"https://{host}"
    body = f"""User-agent: *
Disallow:

Sitemap: {base}/sitemap.xml
"""
    return Response(body, mimetype="text/plain")



@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

if __name__ == "__main__":
    app.run(debug=True)
