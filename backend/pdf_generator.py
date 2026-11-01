"""Generate printable inspection summary PDFs."""
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

NAVY = colors.HexColor("#12243A")
TEAL = colors.HexColor("#087E78")

def create_report(record, path):
    audit, ext = record["audit"], record["extraction"]
    category_info = audit.get("category", record.get("category_info", {}))
    category_name = category_info.get("label", str(record.get("category", "Unclassified")).replace("_", " ").title())
    penalty = audit.get("penalty_assessment", {})
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=17*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#5F6F80"), leading=11))
    story = [Paragraph("NYAY VISION", ParagraphStyle("Brand", parent=styles["Title"], textColor=NAVY, fontSize=19, alignment=TA_LEFT, spaceAfter=2)), Paragraph("PACKAGING COMPLIANCE · INSPECTION SUMMARY", ParagraphStyle("Sub", parent=styles["Normal"], textColor=TEAL, fontSize=9, spaceAfter=15))]
    meta = [["INSPECTION ID", record["scan_id"][:13].upper(), "ISSUED", datetime.fromisoformat(record["created_at"]).strftime("%d %b %Y · %H:%M UTC")], ["AUTO CATEGORY", f"{category_name} · {round(category_info.get('confidence', 0) * 100)}%", "VISION MODEL", ext.get("model_used", "OpenAI")]]
    t = Table(meta, colWidths=[27*mm, 54*mm, 27*mm, 58*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F1F5F8")),("TEXTCOLOR",(0,0),(-1,-1),NAVY),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,colors.white)])); story += [t, Spacer(1, 12)]
    summary = [[
        Paragraph(f"<font size='8' color='#5F6F80'>COMPLIANCE SCORE</font><br/><font size='16' color='#12243A'><b>{audit['score']} / 100</b></font>", styles["BodyText"]),
        Paragraph(f"<font size='8' color='#5F6F80'>OUTCOME</font><br/><font size='12' color='#12243A'><b>{audit['status'].replace('_',' ').upper()}</b></font>", styles["BodyText"]),
        Paragraph(f"<font size='8' color='#5F6F80'>FINDINGS</font><br/><font size='16' color='#12243A'><b>{audit['issues_count']}</b></font>", styles["BodyText"]),
    ]]
    summary_table = Table(summary, colWidths=[55*mm, 55*mm, 55*mm])
    summary_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F8")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LINEBEFORE", (1, 0), (-1, -1), 1, colors.white)]))
    story += [summary_table, Spacer(1, 8)]
    story += [Spacer(1, 10), Paragraph("Penalty exposure", styles["Heading2"]), Paragraph(penalty.get("headline", "Not assessed"), styles["BodyText"])]
    for entry in penalty.get("ranges", []):
        amount = f"INR {entry['maximum_inr']:,}" if entry.get("minimum_inr") == entry.get("maximum_inr") else f"INR {entry.get('minimum_inr', 0):,}–{entry.get('maximum_inr', 0):,}"
        story.append(Paragraph(f"<b>{entry.get('stage', 'Conditional')}: {amount}</b> · {entry.get('law', '')}<br/>{entry.get('qualifier', '')}", styles["SmallMuted"]))
    story.append(Paragraph(penalty.get("basis", "This is an AI-assisted screening aid, not a penalty determination."), styles["SmallMuted"]))
    story += [Spacer(1, 10), Paragraph("Declaration checklist", styles["Heading2"])]
    rows = [["RESULT", "DECLARATION", "REFERENCE", "OBSERVATION"]]
    for c in audit["checks"]:
        rows.append([c["status"].upper(), c["label"], c["reference"], str(c.get("value") or "Not detected")])
    table = Table(rows, colWidths=[20*mm, 68*mm, 30*mm, 48*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7.5),("LEADING",(0,0),(-1,-1),10),("VALIGN",(0,0),(-1,-1),"TOP"),("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#DDE5EA")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FB")]),("BOTTOMPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),7)]))
    story += [table, Spacer(1, 13), Paragraph("Extracted label details", styles["Heading2"])]
    expiry_fallback = "Not detected; applicability is product-specific" if audit.get("expiry_check") != "required" else "Not detected"
    details = [["Product", ext.get("product_name") or "—"], ["Net quantity", ext.get("net_quantity") or "—"], ["MRP", ext.get("mrp") or "—"], ["Pack date", ext.get("pack_date") or "—"], ["Expiry / best before", ext.get("expiry_date") or expiry_fallback], ["Consumer care", ext.get("consumer_care") or "—"], ["Batch / lot", ext.get("batch_number") or "—"]]
    if audit.get("fssai_applicable"):
        details.append(["FSSAI licence", ext.get("fssai_license_number") or "Not detected"])
    dt = Table(details, colWidths=[45*mm, 121*mm]); dt.setStyle(TableStyle([("TEXTCOLOR",(0,0),(0,-1),TEAL),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#E2E8ED")),("BOTTOMPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6)])); story += [dt, Spacer(1, 13), Paragraph("This AI-assisted screening is an operational aid, not a statutory notice or legal opinion. Confirm image readability, package category, exemptions, applicable amendments and state enforcement guidance with a qualified reviewer. Detection is limited to visible declarations. Fine exposure depends on prior offence history and authority adjudication; the image cannot establish that history.", styles["SmallMuted"])]
    doc.build(story)
