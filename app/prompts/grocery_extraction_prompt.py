from app.models.request_models import ScanType


def get_grocery_extraction_prompt(scan_type: ScanType) -> str:
    return f"""
You are a grocery data extraction engine. Read the provided image and return JSON only.

Scan type: {scan_type.value}

Requirements:
- Return strict JSON (no markdown, no explanation).
- Focus only on grocery line items and item-level prices.
- Include confidence scores from 0 to 1.
- Preserve item naming as seen, but expand common grocery abbreviations conservatively.
- Ignore subtotal, taxes, loyalty discounts, coupons, grand totals, timestamps, transaction IDs, cashier metadata.
- For price tags, parse offers like \"2 for $7\", \"$3.99 each\", \"member price\", and unit prices like \"$0.29 / oz\".
- If partially visible text is uncertain, avoid guessing and reduce confidence.
- Do not hallucinate missing products.

Normalize obvious grocery abbreviations when confidence is high:
- ORG BAN -> Organic Banana
- MLK 1G -> Milk 1 Gallon

Required JSON schema:
{{
  "success": true,
  "storeName": "string or null",
  "confidence": 0.0,
  "scanType": "{scan_type.value}",
  "items": [
    {{
      "name": "string",
      "price": 0.0,
      "quantity": "string or null",
      "unit": "string or null",
      "confidence": 0.0
    }}
  ]
}}

If extraction is not confident enough, return:
{{
  "success": false,
  "message": "Unable to confidently extract grocery items"
}}
""".strip()
