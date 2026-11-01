"""Generate readable, officer-oriented packaging inspection reports."""
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

NAVY = colors.HexColor("#12243A")
TEAL = colors.HexColor("#087E78")
MUTED = colors.HexColor("#5F6F80")
GRID = colors.HexColor("#DDE5EA")


def _safe(value):
    """Normalize glyphs unsupported by ReportLab's built-in Helvetica font."""
    value = str(value if value not in (None, "") else "Not detected")
    value = value.replace("₹", "INR ").replace("\u2013", "-").replace("\u2014", "-").replace("\u00b7", " - ")
    return value


def _p(value, style):
    return Paragraph(_safe(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)


def _money(entry):
    low, high = entry.get("minimum_inr", 0), entry.get("maximum_inr", 0)
    if low == high:
        return f"INR {low:,}" if high else "No monetary penalty shown"
    if low == 0:
        return f"Up to INR {high:,}"
    return f"INR {low:,} to INR {high:,}"


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(18 * mm, 12 * mm, 192 * mm, 12 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8 * mm, "NYAY VISION - Officer review aid - Verify against the complete package and current law")
    canvas.drawRightString(192 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def create_report(record, path):
    audit, ext = record["audit"], record["extraction"]
    category = audit.get("category", record.get("category_info", {}))
    category_name = category.get("label", str(record.get("category", "Unclassified")).replace("_", " ").title())
    penalty = audit.get("penalty_assessment", {})
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=15*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=8, leading=11, textColor=MUTED, spaceAfter=3))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=7.2, leading=9.2, wordWrap="CJK", splitLongWords=1))
    styles.add(ParagraphStyle(name="CellSmall", parent=styles["BodyText"], fontSize=6.7, leading=8.5, wordWrap="CJK", splitLongWords=1))
    styles.add(ParagraphStyle(name="CellHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=8, textColor=colors.white))
    styles.add(ParagraphStyle(name="MetaHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=6.7, leading=8, textColor=NAVY))
    styles.add(ParagraphStyle(name="TitleBrand", parent=styles["Title"], textColor=NAVY, fontSize=19, leading=22, alignment=TA_LEFT, spaceAfter=2))
    styles.add(ParagraphStyle(name="Subhead", parent=styles["Normal"], textColor=TEAL, fontSize=8.5, leading=11, spaceAfter=10))

    story = [Paragraph("NYAY VISION", styles["TitleBrand"]), Paragraph("PACKAGING COMPLIANCE - OFFICER INSPECTION AID", styles["Subhead"])]
    created = datetime.fromisoformat(record["created_at"]).strftime("%d %b %Y, %H:%M UTC")
    meta = [
        [_p("INSPECTION ID", styles["MetaHead"]), _p(record["scan_id"][:13].upper(), styles["Cell"]), _p("ISSUED", styles["MetaHead"]), _p(created, styles["Cell"])],
        [_p("AUTO CATEGORY", styles["MetaHead"]), _p(f"{category_name} ({round(category.get('confidence', 0)*100)}% confidence)", styles["Cell"]), _p("VISION MODEL", styles["MetaHead"]), _p(ext.get("model_used", "OpenAI"), styles["Cell"])],
        [_p("IMAGE VIEWS", styles["MetaHead"]), _p(record.get("image_count", ext.get("image_count", 1)), styles["Cell"]), _p("SOURCE FILES", styles["MetaHead"]), _p("; ".join(record.get("image_files", ext.get("source_images", []))) or record.get("filename", "package image"), styles["Cell"])],
    ]
    t = Table(meta, colWidths=[27*mm, 57*mm, 26*mm, 56*mm])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F1F5F8")), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("GRID", (0,0), (-1,-1), 0.5, colors.white)]))
    story += [t, Spacer(1, 9)]

    summary = [[
        Paragraph(f"<font size='8' color='#5F6F80'>SCREENING SCORE</font><br/><font size='15' color='#12243A'><b>{audit.get('score', 0)} / 100</b></font>", styles["BodyText"]),
        Paragraph(f"<font size='8' color='#5F6F80'>SCREENING OUTCOME</font><br/><font size='10' color='#12243A'><b>{_safe(audit.get('status','review')).replace('_',' ').upper()}</b></font>", styles["BodyText"]),
        Paragraph(f"<font size='8' color='#5F6F80'>CONFIRMED IMAGE FINDINGS</font><br/><font size='15' color='#12243A'><b>{audit.get('issues_count', 0)}</b></font>", styles["BodyText"]),
    ]]
    summary_table = Table(summary, colWidths=[55*mm]*3)
    summary_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F1F5F8")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("LINEBEFORE",(1,0),(-1,-1),1,colors.white)]))
    story += [summary_table, Spacer(1, 9)]

    # Officer decisions are explicit and precede any conditional penalty schedule.
    story.append(Paragraph("Officer decision path", styles["Heading2"]))
    actions = [
        ["1", "Confirm product category and scope", "Check the full package, sale channel, pack type, and any category exemption. Correct the auto-category if needed."],
        ["2", "Verify each flagged declaration", "Inspect all sides and readable originals. Mark each finding as confirmed, present elsewhere, exempt, or inconclusive."],
        ["3", "Select the applicable legal route", "Use FSSAI only for a confirmed food-law issue; use Legal Metrology only for a confirmed covered declaration issue. Keep proceedings separate."],
        ["4", "Check offence history and authority", "Verify prior orders/convictions and jurisdiction in official records before selecting a stage or amount."],
        ["5", "Record the decision", "Choose corrective notice, further investigation, referral, or adjudication as authorized; document evidence, reasons, officer, and date."],
    ]
    action_rows = [[_p("STEP", styles["CellHead"]), _p("OFFICER CHOICE", styles["CellHead"]), _p("WHAT TO VERIFY / RECORD", styles["CellHead"])]]
    action_rows += [[_p(a, styles["Cell"]), _p(b, styles["Cell"]), _p(c, styles["Cell"])] for a,b,c in actions]
    at = Table(action_rows, colWidths=[12*mm, 48*mm, 106*mm], repeatRows=1, hAlign="LEFT")
    at.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("GRID",(0,0),(-1,-1),0.4,GRID),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FB")]),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [at, Spacer(1, 8), Paragraph("Conditional penalty schedule", styles["Heading2"])]
    story.append(_p(penalty.get("headline", "No penalty assessment available."), styles["BodyText"]))
    if penalty.get("ranges"):
        p_rows = [[_p("LEGAL ROUTE / STAGE", styles["CellHead"]), _p("STATUTORY AMOUNT", styles["CellHead"]), _p("CONDITION", styles["CellHead"])]]
        for entry in penalty["ranges"]:
            law_stage = f"{escape(_safe(entry.get('law','')))}<br/><b>{escape(_safe(entry.get('stage','Conditional')))}</b>"
            p_rows.append([Paragraph(law_stage, styles["CellSmall"]), _p(_money(entry), styles["Cell"]), _p(entry.get("qualifier", ""), styles["CellSmall"])])
        pt = Table(p_rows, colWidths=[60*mm, 40*mm, 66*mm], repeatRows=1, hAlign="LEFT")
        pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),TEAL),("GRID",(0,0),(-1,-1),0.4,GRID),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FB")]),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story.append(pt)
    else:
        story.append(_p("No monetary range is shown. Confirm the applicable product law and facts before deciding an action.", styles["BodySmall"]))
    story += [Spacer(1, 4), _p(penalty.get("basis", "This is an AI-assisted screening aid, not a penalty determination."), styles["BodySmall"]), _p("Amounts are statutory ceilings/ranges where stated, not a calculated payable fine. Offence stage, legal applicability, authority, evidence, and adjudication are not established by the image. Do not add amounts across separate statutes.", styles["BodySmall"])]

    # Keep the potentially long checklist on its own page so it has a clear header
    # and never breaks immediately after the officer workflow.
    story.append(PageBreak())
    story.append(Paragraph("Declaration checklist", styles["Heading2"]))
    story.append(_p(f"Category applied: {category_name}. Review flags against the complete package; an image omission is not proof that a declaration is absent from the product.", styles["BodySmall"]))
    checks = audit.get("checks", [])
    rows = [[_p("RESULT", styles["CellHead"]), _p("DECLARATION", styles["CellHead"]), _p("LEGAL REFERENCE", styles["CellHead"]), _p("IMAGE OBSERVATION", styles["CellHead"])]]
    for check in checks:
        label = escape(_safe(check.get("label", "")))
        if check.get("severity"):
            label += f"<br/><font color='#5F6F80'>Severity: {escape(_safe(check['severity']))}</font>"
        state = check.get("status", "review").replace("_", " ").upper()
        if state == "NOT APPLICABLE":
            state = "N/A"
        rows.append([_p(state, styles["CellSmall"]), Paragraph(label, styles["CellSmall"]), _p(check.get("reference", ""), styles["CellSmall"]), _p(check.get("detail") or check.get("value") or "Not detected", styles["CellSmall"])])
    checklist = Table(rows, colWidths=[21*mm, 45*mm, 48*mm, 52*mm], repeatRows=1, hAlign="LEFT")
    checklist.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("GRID",(0,0),(-1,-1),0.4,GRID),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FB")]),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [checklist, Spacer(1, 8), Paragraph("Extracted label details", styles["Heading2"])]
    expiry_default = "Not detected - applicability depends on product category" if audit.get("expiry_check") != "required" else "Not detected"
    details = [["Product", ext.get("product_name")], ["Manufacturer / FBO", ext.get("manufacturer_name")], ["Business address", ext.get("manufacturer_address") or ext.get("importer_address")], ["Net quantity", ext.get("net_quantity")], ["MRP", ext.get("mrp")], ["Pack date", ext.get("pack_date")], ["Expiry / best before", ext.get("expiry_date") or expiry_default], ["Consumer care", ext.get("consumer_care")], ["Batch / lot", ext.get("batch_number")]]
    if audit.get("fssai_applicable"):
        details.append(["FSSAI licence", ext.get("fssai_license_number")])
    detail_rows = [[_p(k, styles["Cell"]), _p(v, styles["Cell"])] for k,v in details]
    dt = Table(detail_rows, colWidths=[45*mm, 121*mm], hAlign="LEFT")
    dt.setStyle(TableStyle([("TEXTCOLOR",(0,0),(0,-1),TEAL),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.3,GRID),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story += [dt, Spacer(1, 7), _p("AI-assisted screening only. Confirm image readability, product scope, exemptions, current rules, prior offence history, and jurisdiction. The report is an operational aid, not a statutory notice or legal opinion.", styles["BodySmall"])]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
