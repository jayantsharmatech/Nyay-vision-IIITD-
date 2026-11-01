"""Category-aware screening for common Indian retail package declarations.

The model identifies the product; this module, not the model, selects checks.
"""

CATEGORY_LABELS = {
    "food": "Food",
    "cosmetics_toiletries": "Cosmetics & toiletries",
    "drug_medicine": "Drugs & medicines",
    "medical_device": "Medical device",
    "electronics": "Electronics",
    "apparel": "Apparel & hosiery",
    "household_chemical": "Household chemical",
    "agricultural_produce": "Agricultural produce",
    "agricultural_seed": "Seeds & planting material",
    "industrial_component": "Industrial component",
    "general_nonfood": "General non-food product",
    "other": "Other / unclear product",
}

SEVERITY_POINTS = {"critical": 18, "major": 12, "minor": 6}
FOOD_CATEGORIES = {"food", "agricultural_produce"}

def _check(extraction, key, label, reference, severity="major", *, aliases=(), required=True, review_if_absent=False, detail=None):
    value = extraction.get(key)
    if not value:
        value = next((extraction.get(alias) for alias in aliases if extraction.get(alias)), None)
    if value == "not_applicable":
        value, required, review_if_absent = None, False, False
    elif value in {"not_visible", "unclear"}:
        value, review_if_absent = None, True
    status = ("review" if review_if_absent else "fail" if required else "not_applicable") if not value else "pass"
    return {
        "id": key,
        "label": label,
        "reference": reference,
        "severity": severity if required else "info",
        "status": status,
        "value": value,
        "detail": detail or ("Declaration detected on label." if value else "Required declaration not detected in the submitted image." if required else "Not required for the inferred product category."),
    }

def _rule_checks(extraction, category):
    checks = []
    imported = bool(extraction.get("importer_name") or extraction.get("country_of_origin"))
    responsible_name_aliases = ("importer_name",)
    responsible_address_aliases = ("importer_address",)

    # Common declarations for pre-packaged retail goods. Food date/name rules
    # are routed to FSSAI labeling provisions below.
    if category not in FOOD_CATEGORIES:
        checks.extend([
            _check(extraction, "product_name", "Common or generic product name", "Rule 6(1)(b)", "critical"),
            _check(extraction, "manufacturer_name", "Manufacturer / packer name", "Rule 6(1)(a)", "critical", aliases=responsible_name_aliases),
            _check(extraction, "manufacturer_address", "Responsible business address", "Rule 6(1)(a)", "critical", aliases=responsible_address_aliases),
            _check(extraction, "pack_date", "Month and year of manufacture / packing", "Rule 6(1)(d)", "major"),
        ])
    else:
        checks.extend([
            _check(extraction, "product_name", "Name of the food", "FSS (Labelling and Display) Regulations, 2020, Regulation 5", "critical"),
            _check(extraction, "manufacturer_name", "Food business operator name", "FSS (Labelling and Display) Regulations, 2020, Regulation 5", "critical", aliases=responsible_name_aliases),
            _check(extraction, "manufacturer_address", "Food business operator address", "FSS (Labelling and Display) Regulations, 2020, Regulation 5", "critical", aliases=responsible_address_aliases),
            _check(extraction, "pack_date", "Date of manufacture / packaging", "FSS (Labelling and Display) Regulations, 2020, date marking", "major"),
            _check(extraction, "expiry_date", "Expiry / use-by date", "FSS (Labelling and Display) Regulations, 2020, date marking", "critical"),
            _check(extraction, "batch_number", "Lot / batch identification", "FSS (Labelling and Display) Regulations, 2020", "major"),
            _check(extraction, "fssai_license_number", "FSSAI logo / licence number", "FSS (Labelling and Display) Regulations, 2020", "critical"),
            _check(extraction, "vegetarian_mark", "Vegetarian / non-vegetarian symbol", "FSS (Labelling and Display) Regulations, 2020", "major", required=True, review_if_absent=True, detail="Check the applicable food category and symbol; automatic symbol reading was inconclusive." if extraction.get("vegetarian_mark") in ("unclear", "not_visible") else None),
            _check(extraction, "ingredients", "Ingredient declaration", "FSS (Labelling and Display) Regulations, 2020", "major", required=False, review_if_absent=True, detail="Applicability depends on product type and exemptions; confirm manually."),
            _check(extraction, "nutrition_information", "Nutrition information", "FSS (Labelling and Display) Regulations, 2020", "major", required=False, review_if_absent=True, detail="Applicability depends on product type and exemptions; confirm manually."),
        ])

    # Rule 6 continues to apply to common package declarations for food where
    # FSSAI regulations direct net quantity, MRP and consumer-care particulars.
    checks.extend([
        _check(extraction, "net_quantity", "Net quantity in standard units", "Legal Metrology Act / packaged commodity declarations", "critical"),
        _check(extraction, "mrp", "Retail sale price inclusive of taxes", "Legal Metrology Act / packaged commodity declarations", "critical"),
        _check(extraction, "consumer_care", "Consumer care contact details", "Packaged Commodities Rules, 2011", "major"),
        _check(extraction, "country_of_origin", "Country of origin for imported products", "Rule 6(1)(aa)", "major", required=imported, detail="Declaration detected on label." if extraction.get("country_of_origin") else "Imported product indicated, but country of origin was not detected." if imported else "Not indicated as imported; not checked."),
    ])
    if category == "drug_medicine":
        checks.append(_check(extraction, "expiry_date", "Expiry / potency date", "Drugs Rules, 1945, Rules 96 and 104A", "critical"))
        checks.append(_check(extraction, "batch_number", "Batch number", "Drugs Rules, 1945, Rule 96", "major"))
        checks.append(_check(extraction, "sector_license_number", "Drug licence / manufacturing particulars", "Drugs Rules, 1945", "major", required=False, detail="Sector-specific particulars vary by medicine and pack; manual review required."))
        checks.append({"id": "sector_review", "label": "Medicine-specific particulars", "reference": "Drugs Rules, 1945", "severity": "info", "status": "review", "value": None, "detail": "Schedule, dosage, warning and pack-specific requirements need a medicine-specific review."})
    elif category == "cosmetics_toiletries":
        checks.append(_check(extraction, "batch_number", "Batch / lot number", "Cosmetics Rules, 2020, Rule 34", "major"))
        checks.append(_check(extraction, "sector_license_number", "Cosmetic licence number", "Cosmetics Rules, 2020, Rule 34", "major"))
        checks.append(_check(extraction, "expiry_date", "Use-before / expiry date", "Cosmetics Rules, 2020, Rule 34(c)", "info", required=False, detail="Not failed solely because it is absent; Cosmetics Rule 34 refers to the date, if any."))
        checks.append(_check(extraction, "vegetarian_mark", "Green / red / brown origin dot", "Packaged Commodities Rules, Rule 6(4A)(d), 2026", "major", required=False, review_if_absent=True, detail="The 2026 symbol rule applies to listed cosmetics/toiletries; whether the specific product requires a mark needs review."))
    elif category in {"medical_device", "agricultural_seed", "industrial_component", "apparel", "electronics", "household_chemical", "other"}:
        checks.append({"id": "sector_review", "label": "Product-specific requirements", "reference": "Relevant sector regulations", "severity": "info", "status": "review", "value": None, "detail": "This category can have additional rules, exemptions or pack-specific declarations. Confirm the applicable sector rule set."})
    if not extraction.get("multiple_units"):
        checks.append(_check(extraction, "unit_sale_price", "Unit sale price", "Packaged Commodities Rules, Rule 6(11)", "minor", required=True, detail="Declaration detected on label." if extraction.get("unit_sale_price") else "Unit sale price not detected; confirm applicability and any package-type exception."))
    else:
        checks.append({"id": "unit_sale_price", "label": "Unit sale price", "reference": "Packaged Commodities Rules, Rule 6(11)", "severity": "info", "status": "not_applicable", "value": None, "detail": "Model identified a combination, group or multi-piece package; the specific Rule 6(11) exception needs confirmation."})
    return checks

def _penalty_assessment(category, failed, classification_review):
    if not failed:
        return {"headline": "No potential penalty identified by these checks", "ranges": [], "basis": "No missing required declarations were detected in this image. This is a label screening result, not a legal determination."}
    if classification_review:
        return {"headline": "Manual classification review required", "ranges": [], "basis": "No penalty estimate is shown because the product category or retail-pack scope is uncertain."}
    ranges = []
    failed_ids = {check["id"] for check in failed}
    food_findings = category in FOOD_CATEGORIES and bool(failed_ids & {"product_name", "manufacturer_name", "manufacturer_address", "pack_date", "expiry_date", "batch_number", "fssai_license_number", "vegetarian_mark"})
    lm_declaration_ids = {"net_quantity", "mrp", "consumer_care", "country_of_origin", "unit_sale_price"}
    if category not in FOOD_CATEGORIES:
        lm_declaration_ids |= {"product_name", "manufacturer_name", "manufacturer_address", "pack_date"}
    lm_findings = bool(failed_ids & lm_declaration_ids)
    if food_findings:
        ranges.append({"law": "Food Safety and Standards Act, 2006, Section 52", "minimum_inr": 0, "maximum_inr": 300000, "stage": "Potential misbranded-food penalty cap", "qualifier": "Up to; an adjudicating officer determines applicability and amount."})
    if lm_findings:
        ranges.extend([
            {"law": "Legal Metrology Act, 2009, Section 36(1)", "minimum_inr": 0, "maximum_inr": 0, "stage": "First offence", "qualifier": "Improvement notice; not a monetary penalty."},
            {"law": "Legal Metrology Act, 2009, Section 36(1)", "minimum_inr": 0, "maximum_inr": 500000, "stage": "Second offence", "qualifier": "Penalty may extend to INR 5 lakh."},
            {"law": "Legal Metrology Act, 2009, Section 36(1)", "minimum_inr": 2500000, "maximum_inr": 5000000, "stage": "Subsequent offences", "qualifier": "Fine of INR 25–50 lakh. Do not add this amount to the FSSAI amount."},
        ])
    if food_findings and lm_findings:
        headline = "Conditional exposure · separate statutes; amounts are not additive"
    elif food_findings:
        headline = "Potential statutory exposure · food label"
    elif lm_findings:
        headline = "Conditional statutory exposure · package declarations"
    else:
        headline = "No fine estimate for this finding"
    if not food_findings and not lm_findings:
        return {"headline": headline, "ranges": [], "basis": "The finding is a screening or sector-specific issue without a reliable penalty mapping in this tool. Confirm the applicable product law and facts with a qualified reviewer."}
    return {"headline": headline, "ranges": ranges, "basis": "Screening estimate only. Section 36 offence stages reflect the Legal Metrology amendment effective 1 May 2026. Authority, prior offence history, rule applicability and adjudication affect the actual outcome."}

def evaluate_compliance(extraction):
    category = extraction.get("product_category", "other")
    confidence = float(extraction.get("category_confidence") or 0)
    category_label = CATEGORY_LABELS.get(category, CATEGORY_LABELS["other"])
    scope_uncertain = (not extraction.get("is_prepackaged", False) or extraction.get("sale_channel") in {"non_retail", "industrial_institutional", "unclear"})
    classification_review = confidence < 0.72 or category == "other" or scope_uncertain

    if not extraction.get("is_prepackaged", False):
        checks = [{"id": "scope", "label": "Pre-packaged retail product scope", "reference": "Packaged Commodities Rules, Rules 2–3", "status": "review", "severity": "info", "value": None, "detail": "Image does not clearly show a pre-packaged retail commodity; no mandatory-declaration verdict was generated."}]
    else:
        checks = _rule_checks(extraction, category)

    if confidence < 0.72 or category == "other":
        checks.append({"id": "classification", "label": "Product category confidence", "reference": "AI classification", "status": "review", "severity": "info", "value": f"{round(confidence * 100)}%", "detail": "Classification confidence is low; confirm the product type before relying on category-specific checks."})
    if extraction.get("sale_channel") in {"non_retail", "industrial_institutional", "unclear"}:
        checks.append({"id": "sale_channel", "label": "Retail / institutional scope", "reference": "Packaged Commodities Rules, Rule 3", "status": "review", "severity": "info", "value": extraction.get("sale_channel"), "detail": "Retail exemption depends on end use and direct supply facts that cannot be confirmed from this image."})

    failed = [check for check in checks if check["status"] == "fail"]
    deductions = sum(SEVERITY_POINTS.get(check["severity"], 0) for check in failed)
    score = max(0, 100 - deductions)
    has_review = any(check["status"] == "review" for check in checks)
    status = "manual_review" if has_review else "non_compliant" if failed and score < 70 else "needs_review" if failed else "compliant"
    penalty = _penalty_assessment(category, failed, classification_review or scope_uncertain)
    return {
        "score": score,
        "status": status,
        "checks": checks,
        "issues_count": len(failed),
        "category": {"id": category, "label": category_label, "confidence": confidence, "evidence": extraction.get("category_evidence", [])},
        "fssai_applicable": category in FOOD_CATEGORIES,
        "expiry_check": "required" if category in FOOD_CATEGORIES | {"drug_medicine"} else "product_specific" if category == "cosmetics_toiletries" else "not_generally_required",
        "penalty_assessment": penalty,
    }
