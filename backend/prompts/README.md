# BlueMoxon AI Prompts

This directory contains AI prompts used by the BMX application for book analysis generation.

## Prompt Locations

Prompts are stored in S3 and loaded at runtime with 5-minute caching:
- **Production**: `s3://bluemoxon-images/prompts/`
- **Staging**: `s3://bluemoxon-images-staging/prompts/`

## Deployment

After modifying a prompt, deploy to S3:

```bash
# Deploy to staging first
AWS_PROFILE=bmx-staging aws s3 cp backend/prompts/napoleon-framework/v2.md \
  s3://bluemoxon-images-staging/prompts/napoleon-framework/v2.md

# Test in staging (regenerate a book analysis)
bmx-api POST /books/493/analysis/generate

# Verify output includes required format
bmx-api GET /books/493/analysis/raw | head -30

# If successful, deploy to production
AWS_PROFILE=bmx-prod aws s3 cp backend/prompts/napoleon-framework/v2.md \
  s3://bluemoxon-images/prompts/napoleon-framework/v2.md
```

**Note**: Lambda caches prompts for 5 minutes. Wait or invoke a different book to bypass cache.

## Napoleon Framework Prompts

### `napoleon-framework/v2.md` (Current)

The main prompt for generating book valuation analyses. Produces structured output with:

1. **STRUCTURED-DATA block** (machine-parseable, at start):
   ```
   ---STRUCTURED-DATA---
   CONDITION_GRADE: VG+
   BINDER_IDENTIFIED: Zaehnsdorf
   ...
   ---END-STRUCTURED-DATA---
   ```

2. **13 analysis sections** (human-readable)

3. **METADATA block** (JSON, at end):
   ```
   <!-- METADATA_START -->
   {"is_first_edition": true, ...}
   <!-- METADATA_END -->
   ```

### `napoleon-framework/v1.md` (Legacy)

Original version without structured data block. Kept for reference.

## Parser Support

The markdown parser (`backend/app/utils/markdown_parser.py`) supports both:
- **v2 format**: `---STRUCTURED-DATA---` block
- **Legacy format**: `## SUMMARY\n---\nyaml...`

## Code Reference

- **Loader**: `backend/app/services/bedrock.py` → `load_napoleon_prompt()`
- **Parser**: `backend/app/utils/markdown_parser.py`
- **Summary Extractor**: `backend/app/services/analysis_summary.py`

## Related Documentation

- [Bedrock Integration](../../docs/BEDROCK.md) - Full Bedrock setup and usage
- [Features](../../docs/FEATURES.md) - Napoleon framework feature description
