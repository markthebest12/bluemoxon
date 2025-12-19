# Structured Data Extraction

Extract the following fields from the book analysis below. Output ONLY valid JSON, no other text.

## Required Fields

```json
{
  "condition_grade": "Fine|VG+|VG|VG-|Good+|Good|Fair|Poor",
  "binder_identified": "Binder name or null",
  "binder_confidence": "HIGH|MEDIUM|LOW|NONE",
  "binding_type": "Full Morocco|Half Morocco|Three-Quarter Morocco|Cloth|Boards|Other",
  "valuation_low": 0,
  "valuation_mid": 0,
  "valuation_high": 0,
  "era_period": "Victorian|Romantic|Georgian|Edwardian|Modern",
  "publication_year": 0,
  "is_first_edition": true|false|null,
  "has_provenance": true|false,
  "provenance_tier": "Tier 1|Tier 2|Tier 3|null"
}
```

## Rules

1. Use exact values from the analysis - do not invent data
2. For numeric fields, use integers only (no $ or commas)
3. If a field cannot be determined, use null
4. Output ONLY the JSON object, nothing else

## Analysis to Extract From

```
