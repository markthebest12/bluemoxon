# Two-Stage Structured Data Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement two-stage analysis: (1) generate analysis, (2) extract structured data with a separate focused Bedrock call.

**Architecture:** After `invoke_bedrock()` returns the analysis text, make a second Bedrock call with a simple extraction prompt that takes the analysis as input and outputs JSON. This decouples analysis quality from structured data reliability.

**Tech Stack:** Python, AWS Bedrock (Claude Sonnet), JSON output format

---

## Task 1: Create Extraction Prompt

**Files:**

- Create: `backend/prompts/extraction/structured-data.md`

**Step 1: Write the extraction prompt file**

```markdown
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

```text

**Step 2: Deploy to S3 (staging)**

Run: `AWS_PROFILE=bmx-staging aws s3 cp backend/prompts/extraction/structured-data.md s3://bluemoxon-images-staging/prompts/extraction/structured-data.md`

Expected: `upload: backend/prompts/extraction/structured-data.md to s3://...`

**Step 3: Commit**

```bash
git add backend/prompts/extraction/structured-data.md
git commit -m "feat: add structured data extraction prompt for two-stage approach"
```

---

## Task 2: Add Extraction Function to Bedrock Service

**Files:**

- Modify: `backend/app/services/bedrock.py`
- Test: `backend/tests/test_bedrock.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_bedrock.py`:

```python
def test_extract_structured_data_from_analysis():
    """Test extraction of structured data from analysis text."""
    from app.services.bedrock import extract_structured_data

    # Mock analysis text with typical values
    analysis = """
    ## 1. Executive Summary

    **Condition Grade:** VG+

    The book is bound in full morocco by Zaehnsdorf...

    ### Valuation Summary
    | Estimate | Value |
    |----------|-------|
    | Low | $450 |
    | Mid | $650 |
    | High | $900 |

    Publication year: 1869
    Era: Victorian
    """

    # This will fail until we implement the function
    result = extract_structured_data(analysis)

    assert result is not None
    assert "condition_grade" in result
    assert "valuation_low" in result
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_bedrock.py::test_extract_structured_data_from_analysis -v`

Expected: FAIL with `ImportError: cannot import name 'extract_structured_data'`

**Step 3: Implement the extraction function**

Add to `backend/app/services/bedrock.py` after the existing functions:

```python
# Extraction prompt configuration
EXTRACTION_PROMPT_KEY = "prompts/extraction/structured-data.md"
_extraction_prompt_cache: dict = {"prompt": None, "timestamp": 0}


def load_extraction_prompt() -> str:
    """Load extraction prompt from S3 with caching."""
    global _extraction_prompt_cache

    current_time = time.time()

    if _extraction_prompt_cache["prompt"] and (
        current_time - _extraction_prompt_cache["timestamp"]
    ) < PROMPT_CACHE_TTL:
        return _extraction_prompt_cache["prompt"]

    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=EXTRACTION_PROMPT_KEY)
        prompt = response["Body"].read().decode("utf-8")
        logger.info(f"Loaded extraction prompt from s3://{PROMPTS_BUCKET}/{EXTRACTION_PROMPT_KEY}")
        _extraction_prompt_cache = {"prompt": prompt, "timestamp": current_time}
        return prompt

    except Exception as e:
        logger.warning(f"Failed to load extraction prompt: {e}")
        # Fallback inline prompt
        return """Extract structured data from the analysis. Output ONLY valid JSON:
{
  "condition_grade": "Fine|VG+|VG|VG-|Good+|Good|Fair|Poor or null",
  "binder_identified": "name or null",
  "binder_confidence": "HIGH|MEDIUM|LOW|NONE",
  "binding_type": "type or null",
  "valuation_low": number,
  "valuation_mid": number,
  "valuation_high": number,
  "era_period": "Victorian|Romantic|Georgian|Edwardian|Modern or null",
  "publication_year": number or null,
  "is_first_edition": true|false|null,
  "has_provenance": true|false,
  "provenance_tier": "Tier 1|Tier 2|Tier 3" or null
}"""


def extract_structured_data(analysis_text: str, model: str = "sonnet") -> dict | None:
    """Extract structured data from analysis using a focused Bedrock call.

    Stage 2 of two-stage approach: takes completed analysis and extracts
    machine-readable values via a separate, focused prompt.

    Args:
        analysis_text: The full analysis markdown text
        model: Model to use (default sonnet for speed)

    Returns:
        Dict with extracted values, or None if extraction fails
    """
    if not analysis_text:
        return None

    try:
        client = get_bedrock_client()
        model_id = get_model_id(model)
        extraction_prompt = load_extraction_prompt()

        # Build simple message with analysis appended
        user_message = f"{extraction_prompt}\n\n{analysis_text}\n```"

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,  # JSON output is small
            "messages": [{"role": "user", "content": user_message}],
        })

        logger.info("Invoking Bedrock for structured data extraction")

        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        result_text = response_body["content"][0]["text"].strip()

        # Parse JSON from response (handle potential markdown code blocks)
        json_text = result_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        extracted = json.loads(json_text.strip())
        logger.info(f"Extracted structured data: {list(extracted.keys())}")
        return extracted

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_bedrock.py::test_extract_structured_data_from_analysis -v`

Expected: PASS (may need mocking for actual Bedrock call)

**Step 5: Add mock test for unit testing**

Add to `backend/tests/test_bedrock.py`:

```python
from unittest.mock import patch, MagicMock


def test_extract_structured_data_parses_json():
    """Test that extract_structured_data correctly parses JSON response."""
    from app.services.bedrock import extract_structured_data

    mock_response = {
        "body": MagicMock(
            read=lambda: json.dumps({
                "content": [{"text": '{"condition_grade": "VG+", "valuation_low": 450}'}]
            }).encode()
        )
    }

    with patch("app.services.bedrock.get_bedrock_client") as mock_client:
        mock_client.return_value.invoke_model.return_value = mock_response
        with patch("app.services.bedrock.load_extraction_prompt", return_value="Extract:"):
            result = extract_structured_data("Some analysis text")

    assert result == {"condition_grade": "VG+", "valuation_low": 450}
```

**Step 6: Run all bedrock tests**

Run: `cd backend && poetry run pytest tests/test_bedrock.py -v`

Expected: All tests PASS

**Step 7: Commit**

```bash
git add backend/app/services/bedrock.py backend/tests/test_bedrock.py
git commit -m "feat: add extract_structured_data function for two-stage extraction"
```

---

## Task 3: Integrate Extraction into Worker

**Files:**

- Modify: `backend/app/worker.py`
- Test: `backend/tests/test_worker.py` (if exists, otherwise test via integration)

**Step 1: Modify worker to use two-stage extraction**

In `backend/app/worker.py`, after line 150 (after `invoke_bedrock` returns):

```python
        logger.info(f"Invoking Bedrock for book {book_id}, model={model}")
        analysis_text = invoke_bedrock(messages, model=model)
        logger.info(f"Bedrock returned {len(analysis_text)} chars for book {book_id}")

        # Stage 2: Extract structured data with focused prompt
        from app.services.bedrock import extract_structured_data

        logger.info(f"Extracting structured data for book {book_id}")
        extracted_data = extract_structured_data(analysis_text, model="sonnet")
        if extracted_data:
            logger.info(f"Extracted {len(extracted_data)} fields for book {book_id}")
        else:
            logger.warning(f"No structured data extracted for book {book_id}")
```

**Step 2: Update YAML parsing to prefer extracted data**

Replace lines 156-158 in `backend/app/worker.py`:

```python
        # Parse YAML summary block to extract book field updates
        yaml_data = parse_analysis_summary(analysis_text)
        book_updates = extract_book_updates_from_yaml(yaml_data)
```

With:

```python
        # Prefer Stage 2 extraction, fall back to parsing analysis text
        if extracted_data:
            # Map extracted fields to book update format
            book_updates = {}
            if extracted_data.get("valuation_low"):
                book_updates["value_low"] = Decimal(str(extracted_data["valuation_low"]))
            if extracted_data.get("valuation_high"):
                book_updates["value_high"] = Decimal(str(extracted_data["valuation_high"]))
            if extracted_data.get("valuation_mid"):
                book_updates["value_mid"] = Decimal(str(extracted_data["valuation_mid"]))
            elif "value_low" in book_updates and "value_high" in book_updates:
                book_updates["value_mid"] = (book_updates["value_low"] + book_updates["value_high"]) / 2
            if extracted_data.get("condition_grade"):
                book_updates["condition_grade"] = extracted_data["condition_grade"]
            if extracted_data.get("binding_type"):
                book_updates["binding_type"] = extracted_data["binding_type"]
            # Provenance fields
            if extracted_data.get("has_provenance") is True:
                book_updates["has_provenance"] = True
            if extracted_data.get("provenance_tier"):
                book_updates["provenance_tier"] = extracted_data["provenance_tier"]
            if extracted_data.get("is_first_edition") is not None:
                book_updates["is_first_edition"] = extracted_data["is_first_edition"]

            logger.info(f"Using extracted data for book {book_id}: {list(book_updates.keys())}")
        else:
            # Fall back to parsing analysis text directly
            yaml_data = parse_analysis_summary(analysis_text)
            book_updates = extract_book_updates_from_yaml(yaml_data)
            logger.info(f"Fell back to YAML parsing for book {book_id}")
```

**Step 3: Add Decimal import if not present**

At top of `backend/app/worker.py`, ensure:

```python
from decimal import Decimal
```

**Step 4: Run linter to check syntax**

Run: `cd backend && poetry run ruff check app/worker.py`

Expected: No errors

**Step 5: Commit**

```bash
git add backend/app/worker.py
git commit -m "feat: integrate two-stage extraction into analysis worker"
```

---

## Task 4: Simplify Napoleon Prompt (Optional)

**Files:**

- Modify: `backend/prompts/napoleon-framework/v2.md`

**Step 1: Remove STRUCTURED-DATA requirements from prompt**

Since we're now extracting data separately, we can simplify the prompt by removing:

- Section 0 (STRUCTURED-DATA block requirement)
- The "CRITICAL: Your response will be rejected if..." warning
- The FINAL REMINDER about format

This is optional - the prompt still works without these, but removing them:

1. Reduces prompt length (saves tokens)
2. Removes confusing instructions the AI ignores anyway

**Step 2: Deploy simplified prompt to S3**

Run: `AWS_PROFILE=bmx-staging aws s3 cp backend/prompts/napoleon-framework/v2.md s3://bluemoxon-images-staging/prompts/napoleon-framework/v2.md`

**Step 3: Commit**

```bash
git add backend/prompts/napoleon-framework/v2.md
git commit -m "refactor: remove STRUCTURED-DATA requirements from Napoleon prompt"
```

---

## Task 5: Deploy and Test in Staging

**Files:** None (deployment only)

**Step 1: Push changes to staging branch**

```bash
git push origin HEAD:staging
```

**Step 2: Wait for staging deploy to complete**

Run: `gh run list --workflow deploy-staging.yml --limit 1`

Wait until status shows `completed success`

**Step 3: Generate test analysis**

Run: `bmx-api POST /books/505/analysis/generate`

Expected: `{"job_id": "...", "status": "pending"}`

**Step 4: Wait for job completion (~30-60 seconds)**

Run: `sleep 45`

**Step 5: Check analysis was extracted correctly**

Run: `bmx-api GET /books/505 | jq '{value_low, value_mid, value_high, condition_grade}'`

Expected: Non-null values for all fields

**Step 6: Check Lambda logs for extraction success**

Run: `AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-analysis-worker --since 5m --format short | grep -i extract`

Expected: Lines showing "Extracted X fields for book 505"

---

## Task 6: Deploy to Production

**Files:** None (deployment only)

**Step 1: Create PR from staging to main**

```bash
gh pr create --base main --head staging --title "feat: two-stage structured data extraction (#468)" --body "## Summary
- Adds second Bedrock call to extract structured data reliably
- Decouples analysis quality from data extraction
- Fixes #468

## Test Plan
- [x] Tested in staging with book 505
- [x] Extraction logs show success
- [x] Book fields populated correctly"
```

**Step 2: Merge after CI passes**

```bash
gh pr merge --squash --delete-branch --auto
```

**Step 3: Deploy extraction prompt to production S3**

Run: `AWS_PROFILE=bmx-prod aws s3 cp backend/prompts/extraction/structured-data.md s3://bluemoxon-images/prompts/extraction/structured-data.md`

**Step 4: Verify production deployment**

Run: `bmx-api --prod POST /books/498/analysis/generate`

Wait 60 seconds, then:

Run: `bmx-api --prod GET /books/498 | jq '{value_low, value_mid, value_high, condition_grade}'`

Expected: Non-null values

---

## Summary

After completing all tasks:

1. **Stage 1** (existing): Napoleon analysis generation - unchanged, produces rich markdown
2. **Stage 2** (new): Focused extraction call - reliably extracts 12 structured fields as JSON
3. **Fallback**: If Stage 2 fails, falls back to parsing analysis text directly

The two-stage approach solves the root cause (AI ignoring format instructions) by using a simple, focused extraction prompt that's much harder to ignore.
