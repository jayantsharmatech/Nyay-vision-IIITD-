"""Vision extraction through OpenAI Responses API with model fallback."""
import base64
import json
from openai import AsyncOpenAI
from settings import settings

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "product_category": {"type": "string", "enum": ["food", "cosmetics_toiletries", "drug_medicine", "medical_device", "electronics", "apparel", "household_chemical", "agricultural_produce", "agricultural_seed", "industrial_component", "general_nonfood", "other"]},
        "category_confidence": {"type": "number"}, "category_evidence": {"type": "array", "items": {"type": "string"}},
        "is_prepackaged": {"type": "boolean"}, "sale_channel": {"type": "string", "enum": ["retail", "non_retail", "industrial_institutional", "unclear"]},
        "multiple_units": {"type": "boolean"},
        "product_name": {"type": ["string", "null"]}, "manufacturer_name": {"type": ["string", "null"]},
        "manufacturer_address": {"type": ["string", "null"]}, "importer_name": {"type": ["string", "null"]},
        "importer_address": {"type": ["string", "null"]},
        "country_of_origin": {"type": ["string", "null"]}, "net_quantity": {"type": ["string", "null"]},
        "mrp": {"type": ["string", "null"]}, "unit_sale_price": {"type": ["string", "null"]},
        "pack_date": {"type": ["string", "null"]}, "expiry_date": {"type": ["string", "null"]},
        "consumer_care": {"type": ["string", "null"]}, "batch_number": {"type": ["string", "null"]},
        "fssai_license_number": {"type": ["string", "null"]}, "sector_license_number": {"type": ["string", "null"]},
        "ingredients": {"type": ["string", "null"]}, "nutrition_information": {"type": ["string", "null"]},
        "vegetarian_mark": {"type": "string", "enum": ["green_dot", "brown_dot", "red_dot", "not_visible", "unclear", "not_applicable"]},
        "declarations": {"type": "array", "items": {"type": "string"}},
        "boxes": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "field": {"type": "string"}, "value": {"type": "string"}, "box_2d": {"type": "array", "items": {"type": "integer"}}
        }, "required": ["field", "value", "box_2d"]}},
        "confidence": {"type": "number"}, "notes": {"type": "array", "items": {"type": "string"}}
    }, "required": ["product_category", "category_confidence", "category_evidence", "is_prepackaged", "sale_channel", "multiple_units", "product_name", "manufacturer_name", "manufacturer_address", "importer_name", "importer_address", "country_of_origin", "net_quantity", "mrp", "unit_sale_price", "pack_date", "expiry_date", "consumer_care", "batch_number", "fssai_license_number", "sector_license_number", "ingredients", "nutrition_information", "vegetarian_mark", "declarations", "boxes", "confidence", "notes"]
}

async def extract_label(image: bytes, content_type: str) -> dict:
    if not settings.openai_api_key:
        raise RuntimeError("OpenAI API key is not configured. Add OPENAI_API_KEY to backend/.env and restart the API.")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    data_url = f"data:{content_type};base64,{base64.b64encode(image).decode('ascii')}"
    prompt = "Inspect the submitted Indian product/package image. First identify the physical product category from visible product and label evidence. Choose food, cosmetics_toiletries, drug_medicine, medical_device, electronics, apparel, household_chemical, agricultural_produce, agricultural_seed, industrial_component, general_nonfood, or other. Category confidence must be 0..1 and evidence must cite visible cues; do not infer legal duties. Mark is_prepackaged true only when a predetermined quantity is already packed without the purchaser present. For consumer-ready retail packs, set sale_channel to retail; use non_retail or industrial_institutional only when clearly marked or strongly evidenced; use unclear when image evidence is insufficient. Transcribe only visible text; use null for absent or unreadable values. Capture product/FBO/manufacturer/importer name and address, country of origin, net quantity, MRP, unit price, manufacturing/packing date, expiry/best-before, consumer-care, batch/lot, FSSAI number, other sector license number, ingredients, nutrition panel, and vegetarian mark where visible. For each extracted field, return a tight bounding box as [y_min,x_min,y_max,x_max] on a 0–1000 grid relative to the full image. Never invent text or decide compliance. Confidence is 0..1."
    models = [settings.openai_model, *[m.strip() for m in settings.openai_fallback_models.split(",") if m.strip() and m.strip() != settings.openai_model]]
    failures = []
    for model in models:
        try:
            response = await client.responses.create(
                model=model,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": data_url, "detail": "high"}]}],
                text={"format": {"type": "json_schema", "name": "packaging_label_extraction", "strict": True, "schema": SCHEMA}},
            )
            parsed = json.loads(response.output_text)
            parsed["model_used"] = model
            return parsed
        except Exception as exc:  # retries on transient or model-specific errors
            failures.append(f"{model}: {exc}")
    raise RuntimeError("OpenAI label extraction failed. Check your API key, model access, and image, then retry. " + " | ".join(failures))
