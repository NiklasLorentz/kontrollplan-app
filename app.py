import os
import unicodedata
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from urllib.parse import urljoin
from flask import Flask, render_template, request, send_file, Response
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape

app = Flask(__name__)

# Injicera 'now' i alla templates (används i footer för årstal)
@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}


# ── Health ────────────────────────────────────────────────────
@app.route("/health")
def health():
    return {"ok": True}, 200

@app.route("/ping")
def ping():
    return "pong", 200


# ── Publika sidor ─────────────────────────────────────────────
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

def _send_contact_email(namn: str, avsandare: str, meddelande: str) -> bool:
    """
    Skickar kontaktformulär-meddelande via One.com SMTP till info@kontrollplaner.com.

    Inställningar hämtas från miljövariabler så att lösenordet aldrig
    finns i källkoden.  Sätt dessa i Render → Environment:

        SMTP_HOST     mail.kontrollplaner.com   (eller smtp.one.com)
        SMTP_PORT     587
        SMTP_USER     info@kontrollplaner.com
        SMTP_PASS     ditt-lösenord
        CONTACT_TO    info@kontrollplaner.com
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.one.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "info@kontrollplaner.com")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    to_addr   = os.environ.get("CONTACT_TO", "info@kontrollplaner.com")

    if not smtp_pass:
        # Lösenord ej konfigurerat – logga men krascha inte
        app.logger.warning("SMTP_PASS ej satt – e-post skickades ej.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Kontaktformulär – kontrollplaner.com ({namn})"
        msg["From"]    = smtp_user
        msg["To"]      = to_addr
        msg["Reply-To"] = avsandare

        text_body = (
            f"Nytt meddelande från kontrollplaner.com\n\n"
            f"Namn:   {namn}\n"
            f"E-post: {avsandare}\n\n"
            f"Meddelande:\n{meddelande}\n"
        )
        html_body = f"""
        <div style="font-family:sans-serif;max-width:600px">
          <h2 style="color:#1a3822">Nytt meddelande – kontrollplaner.com</h2>
          <table style="border-collapse:collapse;width:100%">
            <tr><td style="padding:6px 12px;background:#f2faf4;font-weight:600">Namn</td>
                <td style="padding:6px 12px">{namn}</td></tr>
            <tr><td style="padding:6px 12px;background:#f2faf4;font-weight:600">E-post</td>
                <td style="padding:6px 12px"><a href="mailto:{avsandare}">{avsandare}</a></td></tr>
          </table>
          <div style="margin-top:16px;padding:16px;background:#f6faf7;border-left:4px solid #2d6b3d;border-radius:4px">
            <p style="margin:0;white-space:pre-wrap">{meddelande}</p>
          </div>
          <p style="margin-top:16px;font-size:12px;color:#6b8474">
            Skickat via kontaktformuläret på kontrollplaner.com
          </p>
        </div>
        """
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html",  "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_addr, msg.as_string())

        return True

    except Exception as exc:
        app.logger.error(f"SMTP-fel: {exc}")
        return False


@app.route("/kontakt", methods=["GET", "POST"])
def kontakt():
    sent  = False
    error = False
    if request.method == "POST":
        namn       = request.form.get("namn", "").strip()
        avsandare  = request.form.get("email", "").strip()
        meddelande = request.form.get("message", "").strip()
        if namn and avsandare and meddelande:
            ok = _send_contact_email(namn, avsandare, meddelande)
            sent  = ok
            error = not ok
        else:
            error = True
    return render_template("kontakt.html", sent=sent, error=error)


# ── SEO-landningssidor ────────────────────────────────────────
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


# ── Formulär & resultat ───────────────────────────────────────
@app.route("/skapa", methods=["GET", "POST"])
def skapa():
    fields = [
        "bygglovstyp", "byggherre", "telefon", "epost",
        "fastighetsbeteckning", "fastighetsadress",
        "ka_namn", "ka_kontakt", "projektbeskrivning"
    ]
    data = {k: "" for k in fields}
    src = request.form if request.method == "POST" and request.form else request.args
    for k in fields:
        data[k] = src.get(k, "")
    typer = [
        "Nybyggnad (villa/småhus)",
        "Tillbyggnad",
        "Fasadändring",
        "Takomläggning",
        "Garage / Komplementbyggnad",
        "Komplementbostadshus (Attefallsåtgärd)",
        "Altan / Uterum",
        "Pool",
        "Attefallsåtgärder (övrigt)",
    ]
    return render_template("index.html", typer=typer, data=data)

@app.route("/result", methods=["POST"])
def result():
    form = {k: request.form.get(k, "") for k in [
        "bygglovstyp", "byggherre", "telefon", "epost",
        "fastighetsbeteckning", "fastighetsadress",
        "ka_namn", "ka_kontakt", "projektbeskrivning"
    ]}
    rows = plan_rows(form.get("bygglovstyp", ""))
    aktiviteter = activities_for(form.get("bygglovstyp", ""))
    return render_template("result.html", rows=rows, aktiviteter=aktiviteter, **form)


# ── Matchnings-logik ──────────────────────────────────────────
def _normalize(s: str) -> str:
    s = s.strip().lower()
    for char, repl in {"å":"a","ä":"a","ö":"o","é":"e","è":"e","ü":"u"}.items():
        s = s.replace(char, repl)
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

_EXACT_MAP = {
    "nybyggnad (villa/smahus)":               "nybyggnad",
    "tillbyggnad":                            "tillbyggnad",
    "fasadandring":                           "fasad",
    "takomlaggning":                          "tak",
    "garage / komplementbyggnad":             "garage",
    "komplementbostadshus (attefallsatgard)": "komplementbostad",
    "altan / uterum":                         "altan",
    "pool":                                   "pool",
    "attefallsatgarder (ovrigt)":             "attefall",
    "komplementbostadshus":                   "komplementbostad",
    "attefallsatgarder":                      "attefall",
}

_SUBSTRING_MAP = [
    ("komplementbostad",  "komplementbostad"),
    ("nybygg",            "nybyggnad"),
    ("tillbygg",          "tillbyggnad"),
    ("fasad",             "fasad"),
    ("takomlagg",         "tak"),
    ("tak",               "tak"),
    ("garage",            "garage"),
    ("komplementbyggnad", "garage"),
    ("komplement",        "garage"),
    ("altan",             "altan"),
    ("uterum",            "altan"),
    ("pool",              "pool"),
    ("attefall",          "attefall"),
]

def _resolve_typ(bygglovstyp: str) -> str:
    norm = _normalize(bygglovstyp)
    if norm in _EXACT_MAP:
        return _EXACT_MAP[norm]
    for substr, key in _SUBSTRING_MAP:
        if substr in norm:
            return key
    return "okand"


# ── Aktiviteter KA/BN ─────────────────────────────────────────
def activities_for(bygglovstyp: str) -> list:
    typ = _resolve_typ(bygglovstyp)
    if typ not in {"nybyggnad", "tillbyggnad", "garage", "komplementbostad"}:
        return []
    aktiviteter = [
        {"kontroll": "Tekniskt samråd",                          "ansvarig": "KA", "dokumentation": "Protokoll från samråd"},
        {"kontroll": "Platsbesök byggnadsnämnd",                 "ansvarig": "KA", "dokumentation": "Protokoll enl. startbesked"},
        {"kontroll": "Byggplatsbesök KA",                        "ansvarig": "KA", "dokumentation": "Enligt överenskommelse med BN"},
        {"kontroll": "Utlåtande till byggnadsnämnd (slutanmälan)","ansvarig": "KA", "dokumentation": "Skriftligt utlåtande + slutanmälan"},
        {"kontroll": "Slutsamråd",                               "ansvarig": "KA", "dokumentation": "Slutbesked från byggnadsnämnden"},
    ]
    if typ == "komplementbostad":
        aktiviteter = [a for a in aktiviteter if a["kontroll"] != "Tekniskt samråd"]
        aktiviteter.insert(0, {
            "kontroll": "Anmälan till byggnadsnämnd (startbesked)",
            "ansvarig": "BH",
            "dokumentation": "Anmälan, kontrollplan, situationsplan",
        })
    return aktiviteter


# ── Kontrollplansdata ─────────────────────────────────────────
def plan_rows(bygglovstyp: str) -> list:
    typ = _resolve_typ(bygglovstyp)
    return _PLAN_DATA.get(typ, _PLAN_DATA["fallback"])

def _cat(name):
    return {"is_category": True, "kategori": name, "obligatorisk": False}

def _row(kp, vem, hur, mot, nar="Under arbetet", sign="", oblig=False):
    return {"is_category": False, "kontrollpunkt": kp, "vem": vem, "hur": hur,
            "mot": mot, "nar": nar, "signatur": sign, "obligatorisk": oblig}

_PLAN_DATA = {
    "nybyggnad": [
        _cat("Mark och utsättning"),
        _row("Utsättning av byggnad på tomten","BH","Kontrollmätning / inmätning av behörig","Situationsplan, bygglovsbeslut","Före byggstart",oblig=True),
        _row("Markarbete, schakt och fyllning","E","Visuell kontroll, egenkontroll, foto","Ritningar, geoteknisk utredning"),
        _row("Grundläggning (platta/plintar/källare)","E","Egenkontroll, foto","Konstruktionsritningar, BBR"),
        _row("Dränering och fuktskydd mot mark","E","Egenkontroll, foto","BBR avsnitt 6, AMA Hus"),
        _row("Radonspärr / radonåtgärder (om aktuellt)","E","Egenkontroll, foto","BBR avsnitt 6:7"),
        _cat("Stomme och bärande konstruktion"),
        _row("Bärande väggar, pelare och balkar","E","Egenkontroll, foto","Konstruktionsritningar, Eurokoder"),
        _row("Bjälklag (dimensioner, infästningar)","E","Egenkontroll, foto","Konstruktionsritningar"),
        _row("Takstolar / takbjälklag och takresning","E","Egenkontroll, foto","Konstruktionsritningar, tillverkarintyg"),
        _cat("Klimatskal – täthet och isolering"),
        _row("Ytterväggar inkl. isolering, ångskydd och vindskydd","E","Egenkontroll, foto","BBR avsnitt 6 och 9"),
        _row("Yttertak inkl. underlagspapp/duk och takbeläggning","E","Egenkontroll, foto","BBR, tillverkarens anvisningar"),
        _row("Fönster och ytterdörrar (placering, infästning, tätning)","E","Egenkontroll","Ritningar, BBR 6:5"),
        _row("Lufttäthet / täthetsprovning (provtryckning)","E","Provtryckning enl. SS-EN 13829","BBR avsnitt 9:2","Före slutsamråd",oblig=True),
        _cat("Installationer"),
        _row("Elinstallationer","E","Egenkontroll + intyg från behörig elinstallatör","Elsäkerhetslagen, SS 436 40 00"),
        _row("VA-installationer (vatten och avlopp)","E","Täthetsprovning, egenkontroll, intyg","Säker Vatten / Säkra Installationer"),
        _row("Ventilation – typ och dimensionering","E","Egenkontroll, funktionskontroll","BBR avsnitt 6:2"),
        _row("OVK – obligatorisk ventilationskontroll","E","Besiktning av certifierad kontrollant","PBF 5 kap., BBR","Före slutbesked",oblig=True),
        _row("Uppvärmningssystem (om aktuellt)","E","Funktionskontroll, intyg","BBR, tillverkarens anvisningar"),
        _row("Brandskydd (brandvarnare, handbrandsläckare, brandfilt)","BH","Egenkontroll","BBR avsnitt 5, MSB:s rekommendationer"),
        _cat("Tillgänglighet och bostadsutformning"),
        _row("Tillgänglighet för personer med nedsatt rörelseförmåga","BH/E","Måttkontroll mot ritningar","BBR avsnitt 3:1"),
        _row("Rumshöjder och dagsljus uppfylls","BH/E","Måttkontroll","BBR avsnitt 3:1 och 6:3"),
        _cat("Slutkontroll"),
        _row("Utförandet överensstämmer med bygglov och startbesked","BH","Granskning, fotodokumentation, intyg","Bygglovsbeslut, startbesked","Innan slutanmälan",oblig=True),
        _row("Avfall och byggmaterial hanterat korrekt","BH/E","Egenkontroll, mottagningsbevis","Miljöbalken, kommunens riktlinjer"),
    ],
    "tillbyggnad": [
        _cat("Mark och utsättning"),
        _row("Utsättning av tillbyggnaden","BH","Kontrollmätning","Situationsplan, bygglovsbeslut","Före byggstart",oblig=True),
        _row("Markarbete och grundläggning","E","Egenkontroll, foto","Ritningar, BBR"),
        _row("Dränering och fuktskydd mot mark","E","Egenkontroll, foto","BBR avsnitt 6"),
        _cat("Stomme och klimatskal"),
        _row("Bärande stomme (väggar, balkar, pelare)","E","Egenkontroll, foto","Konstruktionsritningar"),
        _row("Yttertak inkl. anslutning mot befintligt tak","E","Egenkontroll, foto","Ritningar, BBR"),
        _row("Ytterväggar inkl. isolering och fuktskydd","E","Egenkontroll","BBR avsnitt 6 och 9"),
        _row("Anslutning mot befintlig byggnad (täthet, köldbryggor, fukt)","E","Egenkontroll, foto","BBR avsnitt 6 och 9"),
        _row("Fönster och dörrar (placering, infästning, tätning)","E","Egenkontroll","Ritningar, BBR 6:5"),
        _cat("Installationer (om aktuellt)"),
        _row("Elinstallationer","E","Intyg från behörig elinstallatör","Elsäkerhetslagen"),
        _row("VA-installationer","E","Intyg","Branschregler Säker Vatten"),
        _row("Ventilation – anslutning/utökning","E","Funktionskontroll","BBR avsnitt 6:2"),
        _row("Brandskydd (brandvarnare, släckare)","BH","Egenkontroll","BBR, MSB"),
        _cat("Slutkontroll"),
        _row("Utförandet överensstämmer med bygglov och startbesked","BH","Granskning, intyg","Bygglovsbeslut, startbesked","Innan slutanmälan",oblig=True),
    ],
    "fasad": [
        _cat("Förberedelse"),
        _row("Åtgärden stämmer med beviljat bygglov och startbesked","BH","Visuell kontroll av handlingar","Bygglovsbeslut, startbesked","Före arbetet",oblig=True),
        _cat("Fasadarbete"),
        _row("Rivning av befintlig fasadbeklädnad (om aktuellt)","E","Foto, egenkontroll","Ritningar"),
        _row("Ny fasadbeklädnad (material, infästningar, sammanfogning)","E","Egenkontroll, foto","Ritningar, BBR, tillverkarens anvisningar"),
        _row("Tätning och fuktskydd (skarvar, anslutningar, socklar)","E","Egenkontroll, foto","BBR avsnitt 6:5"),
        _row("Kulör och material enligt bygglov","BH","Visuell jämförelse","Bygglovsbeslut"),
        _row("Fönster och dörrar (utförande, placering, kulör)","E","Egenkontroll","Ritningar, BBR"),
        _row("Köldbryggor och anslutningar mot takfot / sockel","E","Egenkontroll, foto","BBR avsnitt 9"),
        _cat("Slutkontroll"),
        _row("Utförandet överensstämmer med bygglov och startbesked","BH","Granskning, intyg","Bygglovsbeslut, startbesked","Efter arbetet",oblig=True),
    ],
    "tak": [
        _cat("Rivning och underlag"),
        _row("Befintligt yttertak rivs och omhändertas korrekt","E","Egenkontroll, foto, avfallskvitto","Miljöbalken"),
        _row("Råspont / underlag kontrolleras och lagas vid behov","E","Egenkontroll, foto","Ritningar"),
        _row("Underlagspapp eller underlagsduk monteras korrekt","E","Egenkontroll","Tillverkarens anvisningar, BBR"),
        _cat("Nytt yttertak"),
        _row("Takbeläggning (pannor, plåt, shingel) lagd korrekt","E","Egenkontroll","BBR, tillverkarens anvisningar"),
        _row("Nockning, takfotsavslut och gavlar tätade","E","Egenkontroll, foto","Tillverkarens anvisningar"),
        _row("Takavvattning (hängrännor, stuprör)","E","Egenkontroll","Ritningar"),
        _row("Taksäkerhet (takstegar, glidskydd, gångbrygga)","E","Egenkontroll","PBL, Boverkets föreskrifter, AFS"),
        _row("Genomföringar (skorsten, ventilationshuvar) tätade","E","Egenkontroll, foto","Tillverkarens anvisningar, BBR"),
        _cat("Slutkontroll"),
        _row("Åtgärden stämmer med handling och startbesked","BH","Granskning, egenkontroll","Startbesked","Efter arbetet",oblig=True),
    ],
    "garage": [
        _cat("Läge och utsättning"),
        _row("Placering på tomten enligt situationsplan","BH","Kontrollmätning","Situationsplan, startbesked","Före byggstart",oblig=True),
        _row("Avstånd till tomtgräns kontrolleras","BH","Mätning","PBL 9 kap., startbesked","Före byggstart",oblig=True),
        _cat("Grund och stomme"),
        _row("Grundläggning (betongplatta, plintar)","E","Egenkontroll, foto","Ritningar"),
        _row("Dränering och fuktskydd mot mark","E","Egenkontroll, foto","BBR avsnitt 6"),
        _row("Bärande stomme","E","Egenkontroll","Konstruktionsritningar"),
        _row("Tak och väggar (inkl. isolering om uppvärmt)","E","Egenkontroll","Ritningar"),
        _row("Portar, dörrar och fönster","E","Egenkontroll","Ritningar"),
        _cat("Installationer (om aktuellt)"),
        _row("Elinstallationer","E","Intyg från behörig elinstallatör","Elsäkerhetslagen"),
        _row("Dagvatten och avrinning från hårdgjord yta","E","Visuell kontroll","Kommunens dagvattenkrav"),
        _row("Brandskydd (om garaget är integrerat med bostad)","E","Egenkontroll","BBR avsnitt 5:6"),
        _cat("Slutkontroll"),
        _row("Utförandet överensstämmer med startbesked","BH","Granskning, intyg","Startbesked","Efter arbetet",oblig=True),
    ],
    "komplementbostad": [
        _cat("Anmälan och förberedelse"),
        _row("Anmälan inlämnad och startbesked erhållet","BH","Kontroll av handling","PBL 9 kap. 16 §, startbesked","Före byggstart",oblig=True),
        _row("Placering: min. 4,5 m till tomtgräns (eller grannes medgivande)","BH","Kontrollmätning","PBL 9 kap. 4 a §","Före byggstart",oblig=True),
        _row("Nockhöjd max 4,0 m och max 30 m² BYA","BH","Mätning / granskning","PBL 9 kap. 4 a §","Före byggstart",oblig=True),
        _cat("Grund och stomme"),
        _row("Grundläggning med fuktskydd","E","Egenkontroll, foto","Ritningar, BBR avsnitt 6"),
        _row("Dränering","E","Egenkontroll, foto","BBR avsnitt 6"),
        _row("Bärande stomme","E","Egenkontroll","Konstruktionsritningar"),
        _cat("Klimatskal"),
        _row("Ytterväggar och tak (isolering, täthet, ångskydd)","E","Egenkontroll, foto","BBR avsnitt 6 och 9"),
        _row("Fönster och dörrar – infästning och tätning","E","Egenkontroll","Ritningar, BBR"),
        _cat("Installationer"),
        _row("Elinstallationer","E","Intyg från behörig elinstallatör","Elsäkerhetslagen"),
        _row("VA-installationer (om bostad med vatten/avlopp)","E","Tryckprovning, intyg","Branschregler Säker Vatten"),
        _row("Ventilation","E","Injustering, funktionskontroll","BBR avsnitt 6:2"),
        _row("Brandskydd (brandvarnare, handbrandsläckare, brandfilt)","BH","Egenkontroll","BBR avsnitt 5, MSB"),
        _cat("Slutkontroll"),
        _row("Utförandet överensstämmer med startbesked","BH","Granskning, intyg","Startbesked","Innan slutanmälan",oblig=True),
    ],
    "altan": [
        _cat("Placering och dimensioner"),
        _row("Höjd, utbredning och placering stämmer med handling","BH","Mätning","Situationsplan, startbesked","Före byggstart",oblig=True),
        _row("Avstånd till tomtgräns kontrolleras","BH","Mätning","PBL, kommunens regler"),
        _cat("Byggnation"),
        _row("Grundläggning och infästningar mot befintlig byggnad","E","Egenkontroll, foto","Ritningar"),
        _row("Stomme, reglar och bärande delar","E","Egenkontroll","Konstruktionsritningar"),
        _row("Räcken och fallskydd (höjd min. 1,0 m vid fall > 0,5 m)","E","Måttkontroll, egenkontroll","BBR avsnitt 8:9",oblig=True),
        _row("Ytmaterial (träslag, impregnering, halkskydd)","E","Egenkontroll","Tillverkarens anvisningar"),
        _row("Uterum – glaspartier, tak och tätning (om aktuellt)","E","Egenkontroll","Ritningar, BBR"),
        _row("Dagvatten och avrinning","E","Visuell kontroll","Kommunens dagvattenkrav"),
        _cat("Slutkontroll"),
        _row("Åtgärden stämmer med startbesked / anmälan","BH","Granskning","Startbesked","Efter arbetet",oblig=True),
    ],
    "pool": [
        _cat("Mark och grundarbete"),
        _row("Schakt, markstabilitet och dränering","E","Egenkontroll, foto","Ritningar"),
        _row("Poolskål / platta – utförande och täthet","E","Egenkontroll, tryckprovning","Tillverkarens anvisningar"),
        _row("Backfyllning och ytskikt runt pool","E","Egenkontroll","Ritningar"),
        _cat("Säkerhet (lagkrav)"),
        _row("Inhägnad (staket h. min. 0,9 m) eller täckande skydd","BH","Egenkontroll, mätning","Boverkets råd, PBL","Innan pool tas i bruk",oblig=True),
        _row("Säkerhetsanordning kontrolleras regelbundet","BH","Egenkontroll","MSB"),
        _cat("Teknik"),
        _row("Elinstallationer (pumpar, belysning, värmesystem)","E","Intyg från behörig elinstallatör","Elsäkerhetslagen, IEC 60364-7-702"),
        _row("Vattenrening, cirkulation och kemikaliehantering","E","Egenkontroll","Leverantörens anvisningar"),
        _row("Anslutning till kommunalt VA eller dagvatten (om aktuellt)","BH/E","Egenkontroll","ABVA, kommunens regler"),
        _cat("Slutkontroll"),
        _row("Åtgärden stämmer med eventuellt startbesked","BH","Granskning","Startbesked / handling","Efter arbetet",oblig=True),
    ],
    "attefall": [
        _cat("Anmälan och förberedelse"),
        _row("Anmälan inlämnad och startbesked erhållet","BH","Kontroll av handling","PBL 9 kap. 16 §, startbesked","Före byggstart",oblig=True),
        _row("Mått inom attefallsreglernas gränser (nockhöjd, area)","BH","Kontrollmätning","PBL 9 kap. 4–4 b §§","Före byggstart",oblig=True),
        _row("Avstånd till tomtgräns min. 4,5 m (eller grannes medgivande)","BH","Mätning","PBL 9 kap. 4 §","Före byggstart",oblig=True),
        _cat("Grund och stomme"),
        _row("Grundläggning (plintar/platta) med fuktskydd","E","Egenkontroll, foto","Ritningar, BBR"),
        _row("Bärande stomme","E","Egenkontroll","Ritningar"),
        _row("Tak och tätskikt","E","Egenkontroll","Ritningar"),
        _cat("Klimatskal och ytskikt"),
        _row("Fasadbeklädnad, kulör och material enligt startbesked","BH","Visuell kontroll","Startbesked, bygglovsbeslut"),
        _row("Fönster och dörrar – infästning och tätning","E","Egenkontroll","Ritningar, BBR"),
        _cat("Installationer (om aktuellt)"),
        _row("Elinstallationer","E","Intyg från behörig elinstallatör","Elsäkerhetslagen"),
        _row("VA-installationer","E","Intyg","Branschregler"),
        _row("Brandskydd (brandvarnare, handbrandsläckare)","BH","Egenkontroll","BBR avsnitt 5, MSB"),
        _cat("Slutkontroll"),
        _row("Utförandet överensstämmer med startbesked och anmälan","BH","Granskning, intyg","Startbesked / anmälan","Efter arbetet",oblig=True),
    ],
    "fallback": [
        _cat("Allmänna kontrollpunkter"),
        _row("Åtgärden stämmer med beviljat bygglov / startbesked","BH","Granskning av handling","Bygglovsbeslut / startbesked","Före byggstart",oblig=True),
        _row("Byggmaterial och utförande enligt ritningar","E","Egenkontroll","Ritningar"),
        _row("Installationer utförda av behörig fackman (el, VVS)","E","Intyg","Elsäkerhetslagen, branschregler"),
        _row("Utförandet uppfyller gällande krav","BH","Egenkontroll, intyg","PBL, BBR, startbesked","Innan slutanmälan",oblig=True),
    ],
}


# ── PDF-generator ─────────────────────────────────────────────
def _draw_footer(canvas, doc):
    canvas.saveState()
    try: canvas.setFont("Helvetica", 8)
    except: canvas.setFont("Times-Roman", 8)
    page_width, _ = doc.pagesize
    canvas.drawCentredString(page_width / 2.0, 12, "Skapad via www.kontrollplaner.com")
    canvas.restoreState()


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    form = {k: request.form.get(k, "") for k in [
        "bygglovstyp","byggherre","telefon","epost",
        "fastighetsbeteckning","fastighetsadress",
        "ka_namn","ka_kontakt","projektbeskrivning"
    ]}
    kategorier  = request.form.getlist("kategori[]")
    is_category = request.form.getlist("is_category[]")
    kp   = request.form.getlist("kp[]")
    vem  = request.form.getlist("vem[]")
    hur  = request.form.getlist("hur[]")
    mot  = request.form.getlist("mot[]")
    nar  = request.form.getlist("nar[]")
    sign = request.form.getlist("signatur[]")

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=18, rightMargin=18,
                            topMargin=18, bottomMargin=24)
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)
    head  = ParagraphStyle("head",  parent=styles["Heading1"], fontSize=15, leading=18, spaceAfter=6)

    def P(x, st=small):
        return Paragraph(escape(x or ""), st)

    story = []
    story.append(Paragraph("Kontrollplan – " + escape(form["bygglovstyp"]), head))

    info = [
        ["Byggherre:",           form["byggherre"]],
        ["Telefon:",             form["telefon"]],
        ["E-post:",              form["epost"]],
        ["Fastighetsbeteckning:",form["fastighetsbeteckning"]],
        ["Fastighetsadress:",    form["fastighetsadress"]],
        ["Kontrollansvarig:",    f"{form['ka_namn']} {form['ka_kontakt']}".strip()],
        ["Projektbeskrivning:",  form["projektbeskrivning"]],
    ]
    info_table = Table(info, colWidths=[130, 610])
    info_table.setStyle(TableStyle([
        ("FONTNAME",     (0,0),(0,-1), "Helvetica-Bold"),
        ("VALIGN",       (0,0),(-1,-1),"TOP"),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    headers = ["Kontrollpunkt","Vem","Hur","Kontroll mot","När","Signatur / Datum"]
    data = [[Paragraph("<b>"+h+"</b>", small) for h in headers]]
    category_rows = []
    idx_cat = idx_data = 0

    for flag in is_category:
        if flag == "1":
            title = kategorier[idx_cat] if idx_cat < len(kategorier) else ""
            data.append([P(title),"","","","",""])
            category_rows.append(len(data)-1)
            idx_cat += 1
        else:
            data.append([
                P(kp[idx_data]   if idx_data < len(kp)   else ""),
                P(vem[idx_data]  if idx_data < len(vem)  else ""),
                P(hur[idx_data]  if idx_data < len(hur)  else ""),
                P(mot[idx_data]  if idx_data < len(mot)  else ""),
                P(nar[idx_data]  if idx_data < len(nar)  else ""),
                P(sign[idx_data] if idx_data < len(sign) else ""),
            ])
            idx_data += 1

    table = Table(data, repeatRows=1, colWidths=[230,55,160,160,90,95])
    style = TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), "#1a3822"),
        ("TEXTCOLOR",    (0,0),(-1,0), colors.white),
        ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#d4e6d9")),
        ("VALIGN",       (0,0),(-1,-1),"TOP"),
        ("FONTSIZE",     (0,0),(-1,-1), 8),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ])
    for r in category_rows:
        style.add("SPAN",       (0,r),(-1,r))
        style.add("BACKGROUND", (0,r),(-1,r), "#ddf0e3")
        style.add("FONTNAME",   (0,r),(-1,r), "Helvetica-Bold")
        style.add("TEXTCOLOR",  (0,r),(-1,r), colors.HexColor("#132a1a"))
    table.setStyle(style)
    story.append(table)

    aktiviteter = activities_for(form.get("bygglovstyp",""))
    if aktiviteter:
        story.append(Spacer(1,14))
        story.append(Paragraph("Aktiviteter – Kontrollansvarig och byggnadsnämnd",
            ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=6, spaceAfter=6)))
        akt_headers = ["Aktivitet / Kontroll","Ansvarig","Dokumentation / Kommentar","Datum / Sign."]
        akt_data = [[Paragraph("<b>"+h+"</b>", small) for h in akt_headers]]
        for rad in aktiviteter:
            akt_data.append([P(rad["kontroll"]),P(rad["ansvarig"]),P(rad["dokumentation"]),P("")])
        akt_table = Table(akt_data, colWidths=[210,65,270,145])
        akt_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,0), "#1a3822"),
            ("TEXTCOLOR",    (0,0),(-1,0), colors.white),
            ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#d4e6d9")),
            ("VALIGN",       (0,0),(-1,-1),"TOP"),
            ("FONTSIZE",     (0,0),(-1,-1), 8),
            ("LEFTPADDING",  (0,0),(-1,-1), 4),
            ("RIGHTPADDING", (0,0),(-1,-1), 4),
            ("TOPPADDING",   (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        story.append(akt_table)

    story.append(Spacer(1,12))
    story.append(Paragraph("Härmed intygas att kontrollpunkterna har utförts och att samtliga krav har uppfyllts.", small))
    story.append(Spacer(1,10))
    story.append(Paragraph("Datum: __________________________  Namnteckning: __________________________  Namnförtydligande: __________________________", small))
    story.append(Spacer(1,12))
    story.append(Paragraph("Förkortningar: BH = Byggherre  •  KA = Kontrollansvarig  •  E = Entreprenör (behörig fackman)", small))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="kontrollplan.pdf", mimetype="application/pdf")


# ── SEO ───────────────────────────────────────────────────────
@app.route("/sitemap.xml")
def sitemap_xml():
    host  = request.host or "www.kontrollplaner.com"
    base  = f"https://{host}/"
    today = datetime.now(timezone.utc).date().isoformat()
    pages = [
        {"path": "",                         "changefreq": "weekly",  "priority": "1.0"},
        {"path": "skapa",                    "changefreq": "weekly",  "priority": "0.9"},
        {"path": "kontrollplan-nybyggnad",   "changefreq": "monthly", "priority": "0.8"},
        {"path": "kontrollplan-attefall",    "changefreq": "monthly", "priority": "0.8"},
        {"path": "kontrollplan-tillbyggnad", "changefreq": "monthly", "priority": "0.8"},
        {"path": "kontrollplan-garage",      "changefreq": "monthly", "priority": "0.8"},
        {"path": "faq",                      "changefreq": "monthly", "priority": "0.7"},
        {"path": "kontakt",                  "changefreq": "monthly", "priority": "0.5"},
        {"path": "om",                       "changefreq": "monthly", "priority": "0.5"},
        {"path": "privacy",                  "changefreq": "yearly",  "priority": "0.2"},
        {"path": "terms",                    "changefreq": "yearly",  "priority": "0.2"},
    ]
    xml_items = [f"""  <url>
    <loc>{urljoin(base, p['path'])}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{p['changefreq']}</changefreq>
    <priority>{p['priority']}</priority>
  </url>""" for p in pages]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(xml_items) + "\n</urlset>\n")
    return Response(xml, mimetype="application/xml")

@app.route("/robots.txt")
def robots_txt():
    host = request.host or "www.kontrollplaner.com"
    return Response(f"User-agent: *\nDisallow:\n\nSitemap: https://{host}/sitemap.xml\n",
                    mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)
