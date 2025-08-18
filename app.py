from flask import Flask, render_template, request, send_file
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape

app = Flask(__name__)

# ===========================
# Hälsa & Ping (för Render)
# ===========================
@app.route("/health")
def health():
    return {"ok": True}, 200

@app.route("/ping")
def ping():
    return "pong", 200

# ===========================
# Kontrollplansdata
# ===========================
def plan_rows(bygglovstyp: str):
    """Returnerar standardrader (kategorier + kontrollpunkter) för vald åtgärdstyp."""
    t = (bygglovstyp or "").lower()

    def cat(name):
        return {"is_category": True, "kategori": name, "obligatorisk": False}

    def row(kp, vem, hur, mot, nar="Under arbetet", sign="", oblig=False):
        return {
            "is_category": False,
            "kontrollpunkt": kp,
            "vem": vem,
            "hur": hur,
            "mot": mot,
            "nar": nar,
            "signatur": sign,
            "obligatorisk": oblig,
        }

    if "nybygg" in t:
        return [
            cat("Mark och grund"),
            row("Utsättning av byggnad på tomten", "BH", "Kontrollmätning", "Situationsplan, bygglovsbeslut", "Före byggstart", oblig=True),
            row("Markarbete och schakt", "E", "Visuell kontroll / foto", "Ritningar, PBL"),
            row("Grundläggning inkl. dränering & fuktskydd", "E", "Foto, egenkontroll", "BBR, AMA"),

            cat("Stomme och klimatskal"),
            row("Bärande stomme (väggar, bjälklag, pelare)", "E", "Egenkontroll, foto", "Konstruktionsritningar"),
            row("Takstolar och yttertak", "E", "Egenkontroll, foto", "Ritningar"),
            row("Ytterväggar inkl. isolering & fuktskydd", "E", "Foto, egenkontroll", "BBR"),
            row("Fönster och dörrar (placering, tätning)", "E", "Egenkontroll", "Ritningar, BBR"),

            cat("Installationer"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer (vatten, avlopp)", "E", "Täthetsprov, intyg", "Branschregler"),
            row("Ventilation", "E", "Funktionsprov, OVK-protokoll", "BBR"),
            row("Brandskydd (genomföringar, fasad, ev. eldstad/skorsten)", "E", "Foto, intyg, egenkontroll", "BBR"),
            row("Brandskydd i bostaden (brandvarnare, brandsläckare, brandfilt)", "BH", "Egenkontroll", "BBR, MSB rekommendationer"),
            row("Energikrav (täthetsprov, isolering)", "E", "Provtryckning, intyg", "BBR", "Före slutsamråd"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med beviljat bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Innan slutbesked", oblig=True),
        ]

    if "tillbygg" in t:
        return [
            cat("Mark och grund"),
            row("Utsättning av tillbyggnaden på tomten", "BH", "Kontrollmätning", "Situationsplan, bygglovsbeslut", "Före byggstart", oblig=True),
            row("Markarbete och grundläggning", "E", "Foto, egenkontroll", "Ritningar, BBR"),

            cat("Stomme och klimatskal"),
            row("Bärande stomme (väggar, bjälklag, pelare)", "E", "Egenkontroll, foto", "Konstruktionsritningar"),
            row("Yttertak (anslutning mot befintligt tak)", "E", "Foto, egenkontroll", "Ritningar"),
            row("Ytterväggar inkl. isolering & fuktskydd", "E", "Foto, egenkontroll", "BBR"),
            row("Fönster och dörrar (placering, tätning)", "E", "Egenkontroll", "Ritningar, BBR"),
            row("Anslutning mot befintlig byggnad (täthet, fuktskydd)", "E", "Foto, egenkontroll", "BBR"),

            cat("Installationer"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer (om aktuellt)", "E", "Täthetsprov, intyg", "Branschregler"),
            row("Brandskydd (genomföringar, fasad, ev. eldstad)", "E", "Foto, intyg", "BBR"),
            row("Brandskydd i bostaden (brandvarnare, brandsläckare, brandfilt)", "BH", "Egenkontroll", "BBR, MSB rekommendationer"),
            row("Energikrav (isolering, täthet)", "E", "Provtryckning, intyg", "BBR"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med beviljat bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Innan slutbesked", oblig=True),
        ]

    if "attefall" in t or "komplement" in t:
        return [
            cat("Läge och mått"),
            row("Placering på tomten", "BH", "Kontrollmätning", "Situationsplan, startbesked", "Före byggstart", oblig=True),
            row("Mått (höjd och area)", "BH", "Kontrollmätning", "PBL/PBF", "Före byggstart", oblig=True),

            cat("Byggnation"),
            row("Markarbete och grundläggning", "E", "Foto, egenkontroll", "Ritningar"),
            row("Bärande stomme (väggar, bjälklag, pelare)", "E", "Egenkontroll, foto", "Ritningar"),
            row("Yttertak (lutning, täckning)", "E", "Egenkontroll, foto", "Ritningar"),
            row("Ytterväggar och fasad", "E", "Foto, egenkontroll", "Ritningar, BBR"),
            row("Fönster och dörrar (placering, tätning)", "E", "Egenkontroll", "Ritningar"),

            cat("Installationer (om aktuellt)"),
            row("Elinstallationer", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer", "E", "Intyg", "Branschregler"),
            row("Dagvattenhantering", "E", "Visuell kontroll", "Kommunens krav"),
            row("Brandskydd i bostaden (brandvarnare, brandsläckare, brandfilt)", "BH", "Egenkontroll", "BBR, MSB rekommendationer"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med startbesked", "BH", "Granskning, intyg", "Startbesked", "Innan slutbesked", oblig=True),
        ]

    if "fasad" in t:
        return [
            cat("Fasadåtgärd"),
            row("Åtgärden stämmer med bygglov/startbesked", "BH", "Visuell kontroll", "Bygglovsbeslut, startbesked", "Före arbetet", oblig=True),
            row("Rivning av befintlig fasaddel (om aktuellt)", "E", "Foto, egenkontroll", "Ritningar"),
            row("Ny fasadbeklädnad (material, utförande)", "E", "Foto, egenkontroll", "Ritningar, BBR"),
            row("Färgsättning (ny kulör)", "BH", "Visuell kontroll", "Bygglovsbeslut, startbesked"),
            row("Fönster och dörrar (utförande, placering, kulör)", "E", "Egenkontroll", "Ritningar, BBR"),
            row("Tätning och fuktskydd (skarvar, anslutningar)", "E", "Foto, egenkontroll", "BBR"),
            row("Brandskydd (yttervägg, fasadmaterial)", "E", "Intyg, produktdokumentation", "BBR"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Efter arbetet", oblig=True),
        ]

    if "vent" in t:
        return [
            cat("Installation"),
            row("Installation utförs enligt bygglov/startbesked", "BH", "Granskning, intyg", "Startbesked, ritningar", "Före arbetet", oblig=True),
            row("Montering av ventilationskanaler och aggregat", "E", "Foto, egenkontroll", "Ritningar, BBR"),
            row("Brandskydd vid genomföringar (väggar, bjälklag, tak)", "E", "Foto, intyg", "BBR"),
            row("Isolering av kanaler (värme/kyla)", "E", "Foto, egenkontroll", "BBR"),
            row("Injustering av ventilationsflöden", "E", "Protokoll", "BBR"),
            row("Funktionsprov (OVK)", "E", "OVK-protokoll", "BBR, OVK-regler"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med bygglov/startbesked", "BH", "Granskning, intyg", "Bygglovsbeslut, startbesked", "Efter arbetet", oblig=True),
        ]

    if "riv" in t:
        return [
            cat("Förberedelser"),
            row("Avstängning av el, vatten, avlopp innan rivning", "BH", "Intyg / foto", "Kommunens krav, arbetsmiljöregler", "Före rivning", oblig=True),

            cat("Rivning"),
            row("Rivning utförs enligt startbesked", "E", "Egenkontroll, foto", "Startbesked"),
            row("Sortering och omhändertagande av rivningsmaterial", "E", "Avfallsintyg, foto", "Avfallsförordningen"),
            row("Hantering av farligt avfall (asbest, PCB, olja) om aktuellt", "E", "Intyg", "Miljöbalken"),
            row("Säkerhet på arbetsplatsen (avspärrningar, skydd)", "E", "Egenkontroll", "Arbetsmiljöregler"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med startbesked", "BH", "Intyg", "Startbesked", "Efter rivning", oblig=True),
        ]

    if "eldstad" in t or "skorsten" in t:
        return [
            cat("Installation"),
            row("Installation enligt tillverkarens anvisningar", "E", "Foto, intyg", "Tillverkarens anvisningar"),
            row("Brandskydd (avstånd till brännbart material)", "E", "Foto, egenkontroll", "BBR"),
            row("Skorsten/kanal korrekt monterad och tät", "E", "Tryckprov, intyg", "BBR"),
            row("Sotningsintyg / provtryckning utförd", "Sakkunnig sotare", "Intyg", "Sotningslagen / BBR", oblig=True),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med bygglov/startbesked", "BH", "Intyg", "Startbesked", "Efter installation", oblig=True),
        ]

    if "planlös" in t or "planlos" in t:
        return [
            cat("Bärande och bygg"),
            row("Rivning av bärande väggar (om aktuellt)", "E", "Foto, egenkontroll", "Konstruktionsritning, BBR"),
            row("Ny bärande konstruktion (stålbalk, pelare)", "E", "Foto, intyg", "Ritningar"),
            row("Nya innerväggar (placering, material)", "E", "Egenkontroll", "Ritningar"),
            row("Flytt/ny dörröppning eller fönster (om aktuellt)", "E", "Foto, egenkontroll", "Ritningar"),

            cat("Installationer"),
            row("Elinstallationer (ändringar)", "E", "Intyg", "Elsäkerhetslagen"),
            row("VVS-installationer (om aktuellt)", "E", "Intyg", "Branschregler"),
            row("Brandskydd (nya krav vid ändring)", "E", "Intyg / dokumentation", "BBR"),

            cat("Slutkontroll"),
            row("Utförandet överensstämmer med startbesked", "BH", "Intyg", "Startbesked", "Efter arbetet", oblig=True),
        ]

    if "våtrum" in t or "vatrum" in t or "badrum" in t:
        return [
            cat("Rivning och förberedelse"),
            row("Rivning av gammalt tätskikt", "E", "Foto, egenkontroll", "Branschregler (BBV/GVK)"),
            row("Nya väggar och golv förberedda", "E", "Foto", "Branschregler"),

            cat("Tätskikt och installationer"),
            row("Tätskikt monterat korrekt", "E", "Foto, intyg", "BBV/GVK"),
            row("Golvbrunn (byte/kontroll)", "E", "Foto, intyg", "Säker Vatten"),
            row("Rörgenomföringar tätade", "E", "Foto, intyg", "Säker Vatten"),
            row("Elinstallation (golvvärme, uttag)", "E", "Intyg", "Elsäkerhetslagen"),

            cat("Slutkontroll"),
            row("Slutkontroll av färdigt våtrum", "BH", "Visuell kontroll", "Ritningar, branschregler"),
            row("Utförandet överensstämmer med startbesked", "BH", "Intyg", "Startbesked", "Efter arbetet", oblig=True),
        ]

    # Fallback
    return [cat("Rubrik"), row("Ny kontrollpunkt", "BH", "Egenkontroll", "Ritningar")]

# ===========================
# Routes: formulär → resultat
# ===========================
@app.route('/', methods=['GET','POST'])
def index():
    # Prefill till formuläret om man klickar "Ändra uppgifter" från resultatsidan
    fields = ["bygglovstyp","byggherre","telefon","epost","fastighetsbeteckning","fastighetsadress","ka_namn","ka_kontakt","projektbeskrivning"]
    data = {k: "" for k in fields}
    src = request.form if request.method=='POST' and request.form else request.args
    if src:
        for k in fields:
            data[k] = src.get(k, "")
    typer = [
        "Nybyggnad",
        "Tillbyggnad",
        "Attefallshus / Komplementbyggnad",
        "Fasadändring",
        "Ventilation",
        "Rivning",
        "Eldstad och skorsten",
        "Ändrad planlösning",
        "Våtrumsrenovering",
    ]
    return render_template('index.html', typer=typer, data=data)

@app.route('/result', methods=['POST'])
def result():
    form = {k: request.form.get(k, '') for k in [
        "bygglovstyp","byggherre","telefon","epost","fastighetsbeteckning","fastighetsadress","ka_namn","ka_kontakt","projektbeskrivning"
    ]}
    rows = plan_rows(form["bygglovstyp"])
    return render_template('result.html', rows=rows, **form)

# ===========================
# PDF-generering
# ===========================
@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # 1) Uppgifter
    form = {k: request.form.get(k, '') for k in [
        "bygglovstyp","byggherre","telefon","epost","fastighetsbeteckning","fastighetsadress","ka_namn","ka_kontakt","projektbeskrivning"
    ]}

    # 2) Rader från dolda fält (skapade av JS vid submit)
    kategorier = request.form.getlist('kategori[]')
    is_category = request.form.getlist('is_category[]')
    kp  = request.form.getlist('kp[]')
    vem = request.form.getlist('vem[]')
    hur = request.form.getlist('hur[]')
    mot = request.form.getlist('mot[]')
    nar = request.form.getlist('nar[]')
    sign = request.form.getlist('signatur[]')

    # 3) Bygg PDF
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=10)
    head = ParagraphStyle('head', parent=styles['Heading1'], fontSize=16, leading=18, spaceAfter=6)

    def P(x, st=small):  # säkert paragraph
        return Paragraph(escape(x or ""), st)

    elems = []
    elems.append(Paragraph(f"Kontrollplan – {escape(form['bygglovstyp'])}", head))

    # Uppgiftstabell (etikett fet, värde normal)
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
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elems.append(info_table)
    elems.append(Spacer(1, 10))

    # Kontrollplan-tabell
    headers = ["Kategori/Kontrollpunkt","Vem","Hur","Kontroll mot","När","Signatur / Datum"]
    data = [[Paragraph(f"<b>{h}</b>", small) for h in headers]]
    category_rows = []
    # Viktigt: separata räknare så kategorier/data inte blandas ihop
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
    tstyle = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eef2f7')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ])
    for r in category_rows:
        tstyle.add('SPAN', (0, r), (-1, r))
        tstyle.add('BACKGROUND', (0, r), (-1, r), colors.HexColor('#e8f1ff'))
        tstyle.add('FONTNAME', (0, r), (-1, r), 'Helvetica-Bold')
    table.setStyle(tstyle)
    elems.append(table)

    # Signeringsyta + legend
    elems.append(Spacer(1, 12))
    elems.append(P("Härmed intygas att kontrollpunkterna har utförts och samtliga angivna krav har uppfyllts"))
    elems.append(Spacer(1, 10))
    elems.append(P("Datum: __________________________  Namnteckning: __________________________  Namnförtydligande: __________________________"))
    elems.append(Spacer(1, 12))
    elems.append(P("Förkortningar: BH = Byggherre • KA = Kontrollansvarig • E = Entreprenör"))

    doc.build(elems)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="kontrollplan.pdf", mimetype="application/pdf")

# ===========================
# Lokalt läge
# ===========================
if __name__ == '__main__':
    app.run(debug=True)
