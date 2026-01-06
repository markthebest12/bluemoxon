# Design: Move Inline Imports to Top of File (Issue #809)

**Date:** 2026-01-05
**Issue:** [#809](https://github.com/markthebest12/bluemoxon/issues/809)
**Status:** Approved

## Problem

`backend/app/api/v1/books.py` has 40+ imports scattered inside functions instead of at the top of the file. This violates PEP 8 and makes dependencies harder to understand.

## Solution

Move all inline imports to the top of the file, organized per PEP 8:

1. **Standard library** - `logging`, `datetime`, `decimal`, `tempfile`, `os`, `traceback`, `pathlib`
2. **Third-party** - `boto3`, `fastapi`, `pydantic`, `sqlalchemy`
3. **Local application** - `app.models`, `app.services`, `app.utils`, `app.api`

## Import Consolidation

### Standard Library
```python
import logging
import os
import tempfile
import traceback
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
```

### Third-Party
```python
import boto3
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import exists, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
```

### Local - Models
```python
from app.models import (
    AnalysisJob, Author, Book, BookAnalysis, BookImage,
    EvalRunbook, EvalRunbookJob, Publisher,
)
```

### Local - Services/Utils
Consolidate scattered imports from:
- `app.services.scoring`
- `app.services.tracking`
- `app.services.tracking_poller`
- `app.utils.markdown_parser`
- etc.

## Implementation Steps

1. Create feature branch from `staging`
2. Run full test suite - establish passing baseline
3. Build consolidated import block
4. Edit file - replace import section, delete all inline imports
5. Run full test suite - verify no regressions
6. Run linters - `ruff check` and `ruff format`
7. Create PR to staging (review before merge)
8. After staging validation - PR to main (review before merge)

## Risk Mitigation

- Pure refactoring = no behavior change
- Tests catch any missing/broken imports immediately
- Linter catches unused imports or style issues

## Scope

- 1 file modified: `backend/app/api/v1/books.py`
- ~40 inline import statements removed
- ~15 imports added/consolidated at top
