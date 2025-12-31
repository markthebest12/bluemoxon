# Design: Record AI Model Version in Napoleon Analysis (#715)

**Date:** 2025-12-31
**Issue:** #715
**Status:** Approved

## Overview

Add `model_id` field to track which AI model generated each Napoleon analysis. Enables debugging valuation discrepancies and quality regression detection.

## Design Decisions

1. **Store full model ID** (e.g., `us.anthropic.claude-opus-4-5-20251101-v1:0`)
   - Enables precise version tracking
   - Can strip AWS prefix for display if needed

2. **Nullable column** - existing analyses will show `null`

## Implementation

### 1. Database Schema

```python
# backend/app/models/analysis.py
model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

Migration: `ALTER TABLE book_analyses ADD COLUMN model_id VARCHAR(100);`

### 2. Service Layer

```python
# backend/app/services/bedrock.py
def invoke_bedrock(...) -> tuple[str, str]:
    """Returns (markdown, model_id) tuple."""
    model_id = MODEL_IDS.get(model, MODEL_IDS["sonnet"])
    # ... existing logic ...
    return response_text, model_id
```

### 3. API Endpoints

Update three endpoints:
- `POST /{book_id}/analysis/generate` - save model_id
- `POST /{book_id}/analysis/generate-async` - save model_id
- `GET /{book_id}/analysis` - return model_id in response

### 4. Response Format

```json
{
    "generated_at": "2025-12-31T04:55:25+00:00",
    "model_id": "us.anthropic.claude-opus-4-5-20251101-v1:0",
    ...
}
```

## Test Cases

1. New analysis stores correct model_id
2. GET endpoint returns model_id
3. Existing analyses return null model_id
4. Both sonnet and opus model types work

## Files to Modify

- `backend/app/models/analysis.py` - add column
- `backend/app/services/bedrock.py` - return model_id from invoke_bedrock
- `backend/app/api/v1/books.py` - save and return model_id
- `backend/alembic/versions/` - new migration
