# Session Log: 2026-01-04 - Scraper Browser Crash Investigation

## CRITICAL RULES FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

**IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.**

Key skills for this issue:

- `superpowers:systematic-debugging` - Root cause investigation before fixes
- `superpowers:verification-before-completion` - Evidence before claims, always
- `superpowers:test-driven-development` - For implementing fixes

### 2. Bash Command Formatting - NEVER USE

```text
# comment lines before commands     <- TRIGGERS PERMISSION PROMPT
\ backslash line continuations      <- TRIGGERS PERMISSION PROMPT
$(...) command substitution         <- TRIGGERS PERMISSION PROMPT
|| or && chaining                   <- TRIGGERS PERMISSION PROMPT
! in quoted strings                 <- CORRUPTS VALUES (bash history expansion)
```

### 3. Bash Command Formatting - ALWAYS USE

```bash
# Simple single-line commands
poetry run ruff check backend/

# Separate sequential Bash tool calls instead of &&
# Call 1:
git add -A
# Call 2:
git commit -m "message"

# bmx-api for all BlueMoxon API calls (no permission prompts)
bmx-api GET /books/123
bmx-api --prod POST /health/recalculate-discounts
```

---

## Issue Summary

**Problem:** eBay scraper hangs when importing Australian listing <https://www.ebay.com/itm/373571964136>

**User report:** "second time in a row" - consistent failure

---

## Root Cause Investigation (Phase 1 Complete)

### Lambda Logs Evidence

```text
Log Group: /aws/lambda/bluemoxon-prod-scraper

First attempt (19:33:43):
[INFO] Processing eBay item 373571964136
[INFO] Navigating to https://www.ebay.com/itm/373571964136
[WARNING] No title selector found, continuing anyway
[ERROR] Scraper error: Target page, context or browser has been closed
REPORT Duration: 2972.14 ms, Memory: 1114/2048 MB

Second attempt (19:46:11):
[INFO] Processing eBay item 373571964136
[INFO] Navigating to https://www.ebay.com/itm/373571964136
[WARNING] No title selector found, continuing anyway
[ERROR] Scraper error: Target page, context or browser has been closed
REPORT Duration: 3114.59 ms, Memory: 1114/2048 MB
```

### Key Findings

1. **Lambda is NOT hanging** - Returns 500 error in ~3 seconds
2. **Browser crashes** - Playwright browser dies during page load
3. **Consistent failure** - Same error both attempts
4. **Not memory** - 1114 MB used of 2048 MB available
5. **Not timeout** - Completes in 3s, timeout is 120s

### Error Location in Code

File: `scraper/handler.py`

```python
# Line 357-373: Title selectors that fail
selectors = [
    ".x-item-title",  # Modern eBay layout
    "#itemTitle",     # Older eBay layout
    "[data-testid='x-item-title']",  # Data attribute fallback
    "h1",             # Last resort
]

# Browser crashes between selector check and page.content()
# Error caught at line 516-517:
except Exception as e:
    logger.error(f"Scraper error: {e}")
    return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
```

### Page Analysis

- Listing: Lord Macaulay, History of England (5 vols, 1861)
- Seller: Australian (pm_old_books, Indooroopilly QLD)
- Price: AU $550.00 + AU $128.00 shipping
- Page structure: Standard eBay - no unusual JavaScript/iframes detected
- curl with browser UA: Works fine, returns full HTML
- curl without UA: Returns empty/minimal response (1 byte)

---

## Pattern Analysis (Phase 2 Complete)

| Attribute | Working Listings | Failing Listing |
|-----------|-----------------|-----------------|
| Duration | 14.5s (completes) | 2.9s (crashes) |
| Images | Uploaded to S3 | Never reached |
| Selectors | Found | "No title selector found" |
| Region | Various | Australian seller |

### Root Cause: IP Blocking by eBay

**Breakthrough discovery:** Same URL worked on staging but failed on production.

| Environment | Same URL (226387045267) | Result |
|-------------|------------------------|--------|
| **Production** | No selector found | Crashed in 3s |
| **Staging** | `.x-item-title` found | Success, 9 images uploaded |

**Evidence:**

- Both Lambdas are NOT in a VPC (using Lambda's shared public IP pool)
- Different AWS accounts = different IP pools
- Production IPs were blocked/rate-limited by eBay
- Staging IPs were not blocked

**Why now?** Likely causes:

1. AWS rotated Lambda IPs to a blocked range
2. Cumulative scraping from production account triggered eBay rate limiting
3. FMV search at 19:33:36 (60 listings) may have triggered scrutiny

---

## Resolution: Lambda Redeploy

**Fix applied:** Force new Lambda container to get fresh IP.

```bash
AWS_PROFILE=bmx-prod aws lambda update-function-configuration \
  --function-name bluemoxon-prod-scraper \
  --description "Scraper Lambda - redeployed 2026-01-04T20:25:35Z to refresh IP"
```

**Result:** SUCCESS

```text
Content loaded using selector: .x-item-title ✅
Got HTML: 965784 chars ✅
Uploaded 9 images to S3 ✅
Init Duration: 810.21 ms (cold start confirms new container)
```

---

## Future Mitigations

If this happens again:

1. **Quick fix:** Redeploy Lambda to get new container/IP

   ```bash
   AWS_PROFILE=bmx-prod aws lambda update-function-configuration \
     --function-name bluemoxon-prod-scraper \
     --description "Refresh IP $(date -u +%Y-%m-%dT%H:%M:%SZ)"
   ```

2. **Long-term options:**
   - Add Lambda to VPC with NAT Gateway + Elastic IP (controllable, rotatable)
   - Use proxy service for residential IPs
   - Add retry logic with exponential backoff

---

## Useful Commands

```bash
# Check scraper logs (use actual log group name)
AWS_PROFILE=bmx-prod aws logs describe-log-streams --log-group-name /aws/lambda/bluemoxon-prod-scraper --order-by LastEventTime --descending --limit 3

# Get log events from stream
AWS_PROFILE=bmx-prod aws logs get-log-events --log-group-name /aws/lambda/bluemoxon-prod-scraper --log-stream-name 'STREAM_NAME' --limit 50

# Check Lambda config
AWS_PROFILE=bmx-prod aws lambda get-function-configuration --function-name bluemoxon-prod-scraper --query '[MemorySize,Timeout]'

# Test URL with curl (browser UA required)
curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" "https://www.ebay.com/itm/373571964136" | head -c 1000
```

---

## Session Context

### Completed Earlier This Session

1. **PR #799** - Binder proliferation fix (merged to staging, then main)
2. **PR #800** - Promoted binder fix to production
3. **Binder merge** - Ran `/health/merge-binders` on production
4. **Category updates** - Categorized all 148 PRIMARY books

### PRs Merged

| PR | Description | Status |
|----|-------------|--------|
| #799 | Binder tier mappings + merge endpoint | Merged to main |
| #800 | Promote staging to production | Merged to main |

---

## Files Referenced

- `scraper/handler.py` - Playwright scraper Lambda
- `backend/app/services/scraper.py` - Scraper invocation service
- `backend/app/api/v1/listings.py` - Extract endpoint
- Log group: `/aws/lambda/bluemoxon-prod-scraper`
