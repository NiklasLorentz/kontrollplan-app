import os
from datetime import datetime, timezone
from urllib.parse import urljoin
from flask import Flask, render_template, request, send_file, Response
from io import BytesIO

# ReportLab (PDF)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape

app = Flask(__name__)

# -------------------------
# Health & ping
# -------------------------
@app.route("/health")
def health():
    return {"ok": True}, 200

@app.route("/ping")
def ping():
    return "pong", 200


# -------------------------
# Public pages
# -------------------------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/om")
def om():
    return render_template("om.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/kontakt", methods=["GET","POST"])
def kontakt():
    sent = False
    if request.method == "POST":
        # Här kan du integrera e-posttjänst (Formspree/SendGrid) om/när du vill
        sent = True
    return render_template("kontakt.html", sent=sent)

# -------------------------
# SEO-landningssidor
# -------------------------
@app.route("/kontrollplan-nybyggnad")
def lp_nybyggnad():
    return render_template("kontrollplan_nybyggnad.html")

@app.route("/kontrollplan-attefall")
def lp_attefall():
    return render_template("kontrollplan_attefall.html")

@app.route("/kontrollplan-tillbyggnad")
def lp_tillbyggnad():
    return render_template("kontrollplan_tillbyggnad.html")

@app.route("/kontrollplan-garage")
def lp_garage():
    return render_template("kontrollplan_garage.html")


# -------------------------
# Form & result
# -------------------------
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
        "Komplementbostadshus",
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
    aktiviteter = activities_for(form.get("bygglovstyp",""))
    return render_template("result.html", rows=rows, aktiviteter=aktiviteter, **form)


# -------------------------
# Data helpers (kontrollplan)
# -------------------------
def activities_for(bygglovstyp: str):
    """Tabell 'Aktiviteter KA och byggnadsnämnd' – visas för större åtgärder."""
    t = (bygglovstyp or "").lower()
    if any(s in t for s in ["nybygg", "tillbygg", "garage", "komplement", "komplementbostad"]):
        return [
            {"kontroll":"Tekniskt samråd", "ansvarig":"KA", "dokumentation":"Protokoll"},
            {"kontroll":"Platsbesök BN", "ansvarig":"KA", "dokumentation":"Enl. samråd, protokoll"},
            {"kontroll":"Byggplatsbesök KA", "ansvarig":"KA", "dokumentation":"Enligt ÖK"},
            {"kontroll":"Utlåtande till BN (slutanmälan)", "ansvarig":"KA", "dokumentation":"Utlåtande, slutanmälan"},
            {"kontroll":"Slutsamråd", "ansvarig":"KA", "dokumentation":"Slutbesked"},
        ]
    return []

def plan_rows(bygglovstyp: str):
    """Returnerar föreslagna rader (kategorier + kontrollpunkter) för vald åtgärd."""
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

    if "komplementbostad" in t:
        return [
            cat("Läge och grund"),
            row("Placering enligt situationsplan", "BH", "Kontrollmätning", "Situationsplan, startbesked", "Före byggstart", oblig=True),
            row("Grundläggning (platta/plintar) med fuktskydd", "E", "Egenkontroll, foto", "Ritningar, BBR"),
            cat("Stomme och klimatskal"),
            row("Bärande stomme", "E", "Egenkontroll", "Ritningar"),
            row("Ytterväggar och tak (isolering/täthet)", "E", "Egenkontroll, foto", "BBR"),
            row("Fönster/dörrar – infästning/tätning", "E", "Egenkontroll", "Ritningar, BBR"),
            cat("Installationer"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer", "E", "Tryckprovning/intyg", "Branschregler"),
            row("Ventilation", "E", "Injustering, funktionsprov", "BBR"),
            row("Brandskydd i bostaden (brandvarnare/släckare/brandfilt)", "BH", "Egenkontroll", "BBR, MSB"),
            cat("Slutkontroll"),
            row("Utförandet överensstämmer med startbesked", "BH", "Granskning, intyg", "Startbesked", "Innan slutbesked", oblig=True),
        ]

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
            row("Åtgärden stämmer med ev. startbesked", "BH", "Granskning", "Startbesked/handling", "Efter arbetet", oblig=True),
        ]

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

    # fallback
    return [cat("Rubrik"), row("Ny kontrollpunkt", "BH", "Egenkontroll", "Ritningar")]


# -------------------------
# PDF helpers (footer)
# -------------------------
def _draw_footer(canvas, doc):
    """Ritar fotnot längst ned på varje sida."""
    canvas.saveState()
    try:
        canvas.setFont("Helvetica", 8)
    except:  # fallback
        canvas.setFont("Times-Roman", 8)
    page_width, _ = doc.pagesize
    canvas.drawCentredString(page_width / 2.0, 12, "Skapad via www.kontrollplaner.com")
    canvas.restoreState()


# -------------------------
# PDF generator
# -------------------------
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
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=18, rightMargin=18,
        topMargin=18, bottomMargin=24  # luft för footer
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=10)
    head = ParagraphStyle('head', parent=styles['Heading1'], fontSize=16, leading=18, spaceAfter=6)

    def P(x, st=small):
        return Paragraph(escape(x or ""), st)

    story = []
    story.append(Paragraph("Kontrollplan – " + escape(form['bygglovstyp']), head))

    # Uppgiftsruta
    info = [
        ["Byggherre:", f"{form['byggherre']}"],
        ["Telefon:", f"{form['telefon']}"],
        ["E-post:", f"{form['epost']}"],
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

    # Huvudtabell
    headers = ["Kategori/Kontrollpunkt","Vem","Hur","Kontroll mot","När","Signatur / Datum"]
    data = [[Paragraph("<b>"+h+"</b>", small) for h in headers]]
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

    # Aktiviteter KA/BN (om aktuellt)
    aktiviteter = activities_for(form.get("bygglovstyp",""))
    if aktiviteter:
        story.append(Spacer(1, 14))
        story.append(Paragraph("Aktiviteter KA och byggnadsnämnd", ParagraphStyle('h2', parent=styles['Heading2'], spaceBefore=6, spaceAfter=6)))
        akt_headers = ["Kontroll","Ansvarig","Dokumentation/kommentar","Datum/sign"]
        akt_data = [[Paragraph("<b>"+h+"</b>", small) for h in akt_headers]]
        for rad in aktiviteter:
            akt_data.append([P(rad['kontroll']), P(rad['ansvarig']), P(rad['dokumentation']), P("")])
        akt_table = Table(akt_data, colWidths=[220, 70, 260, 120])
        akt_table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),'#eef2f7'),
            ('GRID',(0,0),(-1,-1),0.5,colors.black),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('FONTSIZE',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),4),
            ('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),4),
            ('BOTTOMPADDING',(0,0),(-1,-1),4)
        ]))
        story.append(akt_table)

    # Signeringsrad + legend
    story.append(Spacer(1,12))
    story.append(Paragraph("Härmed intygas att kontrollpunkterna har utförts och samtliga angivna krav har uppfyllts", small))
    story.append(Spacer(1,10))
    story.append(Paragraph("Datum: __________________________  Namnteckning: __________________________  Namnförtydligande: __________________________", small))
    story.append(Spacer(1,12))
    story.append(Paragraph("Förkortningar: BH = Byggherre • KA = Kontrollansvarig • E = Entreprenör", small))

    # Bygg PDF (med footer på alla sidor)
    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="kontrollplan.pdf", mimetype="application/pdf")


# -------------------------
# SEO: sitemap & robots
# -------------------------
@app.route("/sitemap.xml")
def sitemap_xml():
    host = request.host or "www.kontrollplaner.com"
    base = f"https://{host}/"
    today = datetime.now(timezone.utc).date().isoformat()
    pages = [
        {"path": "",                        "changefreq": "weekly",  "priority": "1.0"},
        {"path": "skapa",                   "changefreq": "weekly",  "priority": "0.9"},
        {"path": "kontrollplan-nybyggnad",  "changefreq": "monthly", "priority": "0.8"},
        {"path": "kontrollplan-attefall",   "changefreq": "monthly", "priority": "0.8"},
        {"path": "kontrollplan-tillbyggnad","changefreq": "monthly", "priority": "0.8"},
        {"path": "kontrollplan-garage",     "changefreq": "monthly", "priority": "0.8"},
        {"path": "kontakt",                 "changefreq": "monthly", "priority": "0.6"},
        {"path": "om",                      "changefreq": "monthly", "priority": "0.6"},
        {"path": "faq",                     "changefreq": "monthly", "priority": "0.6"},
        {"path": "privacy",                 "changefreq": "yearly",  "priority": "0.3"},
        {"path": "terms",                   "changefreq": "yearly",  "priority": "0.3"},
    ]

    def loc_url(path): 
        return urljoin(base, path)

    xml_items = []
    for p in pages:
        xml_items.append(
            f"""  <url>
    <loc>{loc_url(p['path'])}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{p['changefreq']}</changefreq>
    <priority>{p['priority']}</priority>
  </url>"""
        )

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
    body = f"User-agent: *\nDisallow:\n\nSitemap: {base}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    # För lokal utveckling
    app.run(debug=True)
