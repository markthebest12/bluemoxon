# Phase 8: Paste-to-Extract Order Details - Implementation Plan

## Overview
Implement the paste-to-extract feature as designed in `2025-12-12-paste-order-extraction-design.md`.

## Task 1: Admin Config Infrastructure

### 1.1 Create Database Migration
**File:** `backend/alembic/versions/XXXX_add_admin_config_table.py`

```python
"""Add admin_config table

Revision ID: generate_new
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'admin_config',
        sa.Column('key', sa.String(50), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    # Seed default values
    op.execute("""
        INSERT INTO admin_config (key, value) VALUES
        ('gbp_to_usd_rate', '1.28'),
        ('eur_to_usd_rate', '1.10')
    """)

def downgrade():
    op.drop_table('admin_config')
```

Generate with: `cd backend && poetry run alembic revision -m "add_admin_config_table"`

### 1.2 Create Admin Config Model
**File:** `backend/app/models/admin_config.py`

```python
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class AdminConfig(Base):
    __tablename__ = "admin_config"

    key = Column(String(50), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 1.3 Create Admin API Endpoints
**File:** `backend/app/api/v1/admin.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.admin_config import AdminConfig
from app.api.v1.auth import get_current_admin_user

router = APIRouter()

class ConfigResponse(BaseModel):
    gbp_to_usd_rate: float
    eur_to_usd_rate: float

class ConfigUpdate(BaseModel):
    gbp_to_usd_rate: Optional[float] = None
    eur_to_usd_rate: Optional[float] = None

@router.get("/config", response_model=ConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdminConfig))
    configs = {c.key: c.value for c in result.scalars().all()}
    return ConfigResponse(
        gbp_to_usd_rate=float(configs.get("gbp_to_usd_rate", 1.28)),
        eur_to_usd_rate=float(configs.get("eur_to_usd_rate", 1.10))
    )

@router.put("/config", response_model=ConfigResponse)
async def update_config(
    updates: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _user = Depends(get_current_admin_user)
):
    for key, value in updates.model_dump(exclude_none=True).items():
        config = await db.get(AdminConfig, key)
        if config:
            config.value = value
        else:
            db.add(AdminConfig(key=key, value=value))
    await db.commit()
    return await get_config(db)
```

Register in `backend/app/api/v1/__init__.py`:
```python
from app.api.v1 import admin
router.include_router(admin.router, prefix="/admin", tags=["admin"])
```

### 1.4 Create AdminConfigView.vue
**File:** `frontend/src/views/AdminConfigView.vue`

```vue
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/services/api";

const config = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.10 });
const saving = ref(false);
const message = ref("");

async function loadConfig() {
  const res = await api.get("/admin/config");
  config.value = res.data;
}

async function saveConfig() {
  saving.value = true;
  message.value = "";
  try {
    await api.put("/admin/config", config.value);
    message.value = "Saved successfully";
  } catch (e) {
    message.value = "Failed to save";
  } finally {
    saving.value = false;
  }
}

onMounted(loadConfig);
</script>

<template>
  <div class="max-w-2xl mx-auto p-6">
    <h1 class="text-2xl font-bold mb-6">Admin Configuration</h1>
    <div class="bg-white rounded-lg shadow p-6 space-y-4">
      <h2 class="text-lg font-semibold">Currency Conversion Rates</h2>
      <div class="grid grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm text-gray-700">GBP to USD</span>
          <input v-model.number="config.gbp_to_usd_rate" type="number" step="0.01"
            class="mt-1 block w-full rounded border-gray-300 shadow-sm" />
        </label>
        <label class="block">
          <span class="text-sm text-gray-700">EUR to USD</span>
          <input v-model.number="config.eur_to_usd_rate" type="number" step="0.01"
            class="mt-1 block w-full rounded border-gray-300 shadow-sm" />
        </label>
      </div>
      <div class="flex items-center gap-4">
        <button @click="saveConfig" :disabled="saving"
          class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <span v-if="message" class="text-sm text-green-600">{{ message }}</span>
      </div>
    </div>
  </div>
</template>
```

Add route in `frontend/src/router/index.ts`:
```typescript
{
  path: "/admin/config",
  name: "admin-config",
  component: () => import("@/views/AdminConfigView.vue"),
  meta: { requiresAuth: true, requiresAdmin: true }
}
```

**Verification:** Visit `/admin/config`, update a rate, refresh page, confirm it persists.

---

## Task 2: Order Extractor Service

### 2.1 Create Regex Extractor
**File:** `backend/app/services/order_extractor.py`

```python
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class FieldResult(BaseModel):
    value: any
    confidence: float

class ExtractionResult(BaseModel):
    order_number: Optional[str] = None
    item_price: Optional[float] = None
    shipping: Optional[float] = None
    total: Optional[float] = None
    currency: str = "USD"
    purchase_date: Optional[str] = None
    platform: str = "eBay"
    estimated_delivery: Optional[str] = None
    tracking_number: Optional[str] = None
    confidence: float = 0.0
    used_llm: bool = False
    field_confidence: dict = {}

PATTERNS = {
    "order_number": [
        (r"\b(\d{2}-\d{5}-\d{5})\b", 0.99),  # eBay format
        (r"[Oo]rder\s*(?:#|number|num)?[:\s]*(\d[\d-]+\d)", 0.95),
    ],
    "total": [
        (r"[Oo]rder\s+[Tt]otal[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.95),
        (r"[Tt]otal[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.90),
    ],
    "item_price": [
        (r"[Ii]tem\s+[Pp]rice[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.95),
        (r"[Pp]rice[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.85),
    ],
    "shipping": [
        (r"[Ss]hipping[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.95),
        (r"[Pp]ostage[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.90),
    ],
    "tracking": [
        (r"\b(\d{20,30})\b", 0.85),  # Long numeric tracking
        (r"[Tt]racking[:\s#]*([A-Z0-9]{10,30})", 0.95),
    ],
    "date": [
        (r"(\w{3}\s+\d{1,2},?\s+\d{4})", 0.90),  # Jan 15, 2025
        (r"(\d{4}-\d{2}-\d{2})", 0.95),  # ISO format
        (r"(\d{1,2}/\d{1,2}/\d{4})", 0.85),  # MM/DD/YYYY
    ],
    "delivery": [
        (r"[Ee]stimated\s+[Dd]elivery[:\s]+(.+?)(?:\n|$)", 0.90),
        (r"[Dd]elivery[:\s]+(\w{3}\s+\d{1,2}(?:\s*-\s*\d{1,2})?)", 0.85),
    ],
}

CURRENCY_MAP = {"£": "GBP", "$": "USD", "€": "EUR"}

def parse_price(match: tuple) -> tuple[str, float]:
    """Parse currency symbol and amount from regex match."""
    currency_symbol, amount = match
    currency = CURRENCY_MAP.get(currency_symbol, "USD")
    value = float(amount.replace(",", ""))
    return currency, value

def extract_with_regex(text: str) -> ExtractionResult:
    """Extract order details using regex patterns."""
    result = ExtractionResult()
    field_confidence = {}

    # Order number
    for pattern, conf in PATTERNS["order_number"]:
        match = re.search(pattern, text)
        if match:
            result.order_number = match.group(1)
            field_confidence["order_number"] = conf
            break

    # Prices (total, item_price, shipping)
    for field in ["total", "item_price", "shipping"]:
        for pattern, conf in PATTERNS[field]:
            match = re.search(pattern, text)
            if match:
                currency, value = parse_price(match.groups())
                setattr(result, field, value)
                if field == "total":
                    result.currency = currency
                field_confidence[field] = conf
                break

    # Tracking number
    for pattern, conf in PATTERNS["tracking"]:
        match = re.search(pattern, text)
        if match:
            result.tracking_number = match.group(1)
            field_confidence["tracking_number"] = conf
            break

    # Purchase date
    for pattern, conf in PATTERNS["date"]:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                # Try multiple date formats
                for fmt in ["%b %d, %Y", "%b %d %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        result.purchase_date = dt.strftime("%Y-%m-%d")
                        field_confidence["purchase_date"] = conf
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
            if result.purchase_date:
                break

    # Estimated delivery
    for pattern, conf in PATTERNS["delivery"]:
        match = re.search(pattern, text)
        if match:
            result.estimated_delivery = match.group(1).strip()
            field_confidence["estimated_delivery"] = conf
            break

    # Calculate overall confidence
    if field_confidence:
        result.confidence = sum(field_confidence.values()) / len(field_confidence)
    result.field_confidence = field_confidence

    return result
```

### 2.2 Add Unit Tests
**File:** `backend/tests/test_order_extractor.py`

```python
import pytest
from app.services.order_extractor import extract_with_regex

SAMPLE_EBAY_EMAIL = """
Your order has been confirmed!
Order number: 21-13904-88107

Item: First Edition Book
Item price: £239.00
Shipping: £17.99
Order total: £256.99

Estimated delivery: Jan 20-25

Tracking number: 9400111899223847560123
"""

def test_extracts_order_number():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.order_number == "21-13904-88107"
    assert result.field_confidence["order_number"] >= 0.95

def test_extracts_prices():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.item_price == 239.00
    assert result.shipping == 17.99
    assert result.total == 256.99
    assert result.currency == "GBP"

def test_extracts_tracking():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.tracking_number == "9400111899223847560123"

def test_overall_confidence():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.confidence >= 0.8

def test_empty_text():
    result = extract_with_regex("")
    assert result.confidence == 0.0
    assert result.order_number is None

def test_partial_extraction():
    text = "Order total: $50.00"
    result = extract_with_regex(text)
    assert result.total == 50.00
    assert result.currency == "USD"
    assert result.order_number is None
```

Run: `cd backend && poetry run pytest tests/test_order_extractor.py -v`

---

## Task 3: Extract API Endpoint

### 3.1 Create Orders Router
**File:** `backend/app/api/v1/orders.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json

from app.database import get_db
from app.models.admin_config import AdminConfig
from app.services.order_extractor import extract_with_regex, ExtractionResult
from app.services.bedrock import get_bedrock_client

router = APIRouter()

class ExtractRequest(BaseModel):
    text: str

class ExtractResponse(BaseModel):
    order_number: Optional[str] = None
    item_price: Optional[float] = None
    shipping: Optional[float] = None
    total: Optional[float] = None
    currency: str = "USD"
    total_usd: Optional[float] = None
    purchase_date: Optional[str] = None
    platform: str = "eBay"
    estimated_delivery: Optional[str] = None
    tracking_number: Optional[str] = None
    confidence: float = 0.0
    used_llm: bool = False
    field_confidence: dict = {}

LLM_PROMPT = """Extract order details from this text. Return JSON only:
{
  "order_number": "string or null",
  "item_price": number or null,
  "shipping": number or null,
  "total": number or null,
  "currency": "USD|GBP|EUR",
  "purchase_date": "YYYY-MM-DD or null",
  "estimated_delivery": "string or null",
  "tracking_number": "string or null"
}

Text:
"""

async def extract_with_llm(text: str) -> dict:
    """Use Bedrock Claude to extract order details."""
    client = get_bedrock_client()
    response = client.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": LLM_PROMPT + text}]
        })
    )
    result = json.loads(response["body"].read())
    content = result["content"][0]["text"]
    # Extract JSON from response
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON in response
        import re
        match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}

async def get_conversion_rate(currency: str, db: AsyncSession) -> float:
    """Get currency conversion rate from admin config."""
    if currency == "USD":
        return 1.0
    key = f"{currency.lower()}_to_usd_rate"
    config = await db.get(AdminConfig, key)
    if config:
        return float(config.value)
    # Fallback defaults
    return {"GBP": 1.28, "EUR": 1.10}.get(currency, 1.0)

@router.post("/extract", response_model=ExtractResponse)
async def extract_order(
    request: ExtractRequest,
    db: AsyncSession = Depends(get_db)
):
    if not request.text.strip():
        raise HTTPException(400, "Text is required")

    # Try regex first
    result = extract_with_regex(request.text)

    # If confidence too low, try LLM
    if result.confidence < 0.8:
        try:
            llm_result = await extract_with_llm(request.text)
            if llm_result:
                # Merge LLM results with higher confidence
                for field, value in llm_result.items():
                    if value is not None:
                        current_conf = result.field_confidence.get(field, 0)
                        if current_conf < 0.7:
                            setattr(result, field, value)
                            result.field_confidence[field] = 0.85
                result.used_llm = True
                # Recalculate overall confidence
                if result.field_confidence:
                    result.confidence = sum(result.field_confidence.values()) / len(result.field_confidence)
        except Exception as e:
            # Log but continue with regex results
            print(f"LLM extraction failed: {e}")

    # Convert to USD if needed
    response = ExtractResponse(**result.model_dump())
    if response.total and response.currency != "USD":
        rate = await get_conversion_rate(response.currency, db)
        response.total_usd = round(response.total * rate, 2)
    elif response.total:
        response.total_usd = response.total

    return response
```

Register in `backend/app/api/v1/__init__.py`:
```python
from app.api.v1 import orders
router.include_router(orders.router, prefix="/orders", tags=["orders"])
```

**Verification:**
```bash
bmx-api POST /orders/extract '{"text": "Order number: 21-13904-88107\nOrder total: £256.99"}'
```

---

## Task 4: PasteOrderModal Component

### 4.1 Create Component
**File:** `frontend/src/components/PasteOrderModal.vue`

```vue
<script setup lang="ts">
import { ref } from "vue";
import { api } from "@/services/api";

interface ExtractedData {
  order_number?: string;
  item_price?: number;
  shipping?: number;
  total?: number;
  currency?: string;
  total_usd?: number;
  purchase_date?: string;
  platform?: string;
  estimated_delivery?: string;
  tracking_number?: string;
  confidence: number;
  used_llm: boolean;
  field_confidence: Record<string, number>;
}

const emit = defineEmits<{
  close: [];
  apply: [data: ExtractedData];
}>();

const pastedText = ref("");
const extractedData = ref<ExtractedData | null>(null);
const extracting = ref(false);
const error = ref("");

async function handleExtract() {
  if (!pastedText.value.trim()) {
    error.value = "Please paste order text";
    return;
  }

  extracting.value = true;
  error.value = "";

  try {
    const res = await api.post("/orders/extract", { text: pastedText.value });
    extractedData.value = res.data;

    if (!res.data.order_number && !res.data.total) {
      error.value = "Could not extract order details. Try a different format.";
      extractedData.value = null;
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Extraction failed";
  } finally {
    extracting.value = false;
  }
}

function handleApply() {
  if (extractedData.value) {
    emit("apply", extractedData.value);
  }
}

function handleBack() {
  extractedData.value = null;
  error.value = "";
}

function getConfidenceIcon(field: string): string {
  const conf = extractedData.value?.field_confidence[field] || 0;
  return conf >= 0.8 ? "✓" : "⚠️";
}

function getConfidenceClass(field: string): string {
  const conf = extractedData.value?.field_confidence[field] || 0;
  return conf >= 0.8 ? "text-green-600" : "text-yellow-600";
}

async function copyTracking() {
  if (extractedData.value?.tracking_number) {
    await navigator.clipboard.writeText(extractedData.value.tracking_number);
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="emit('close')">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
      <div class="p-4 border-b flex justify-between items-center">
        <h2 class="text-lg font-semibold">
          {{ extractedData ? "Extracted Order Details" : "Paste Order Details" }}
        </h2>
        <button @click="emit('close')" class="text-gray-500 hover:text-gray-700">✕</button>
      </div>

      <!-- Input State -->
      <div v-if="!extractedData" class="p-4 space-y-4">
        <p class="text-sm text-gray-600">
          Paste your eBay order confirmation email text below.
        </p>
        <textarea
          v-model="pastedText"
          rows="10"
          class="w-full border rounded-lg p-3 text-sm font-mono"
          placeholder="Your order has been confirmed!&#10;Order number: 21-13904-88107&#10;..."
        ></textarea>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <div class="flex justify-end gap-2">
          <button @click="emit('close')" class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">
            Cancel
          </button>
          <button
            @click="handleExtract"
            :disabled="extracting"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {{ extracting ? "Extracting..." : "Extract" }}
          </button>
        </div>
      </div>

      <!-- Results State -->
      <div v-else class="p-4 space-y-4">
        <div v-if="extractedData.used_llm" class="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded inline-block">
          Enhanced with AI
        </div>

        <div class="space-y-2">
          <div v-if="extractedData.order_number" class="flex justify-between items-center">
            <span class="text-sm text-gray-600">Order Number</span>
            <span class="font-medium flex items-center gap-1">
              {{ extractedData.order_number }}
              <span :class="getConfidenceClass('order_number')">{{ getConfidenceIcon('order_number') }}</span>
            </span>
          </div>

          <div v-if="extractedData.total" class="flex justify-between items-center">
            <span class="text-sm text-gray-600">Total</span>
            <span class="font-medium flex items-center gap-1">
              {{ extractedData.currency === 'GBP' ? '£' : extractedData.currency === 'EUR' ? '€' : '$' }}{{ extractedData.total?.toFixed(2) }}
              <span v-if="extractedData.total_usd && extractedData.currency !== 'USD'" class="text-gray-500">
                (${{ extractedData.total_usd?.toFixed(2) }})
              </span>
              <span :class="getConfidenceClass('total')">{{ getConfidenceIcon('total') }}</span>
            </span>
          </div>

          <div v-if="extractedData.item_price" class="flex justify-between items-center">
            <span class="text-sm text-gray-600">Item Price</span>
            <span class="font-medium flex items-center gap-1">
              {{ extractedData.currency === 'GBP' ? '£' : extractedData.currency === 'EUR' ? '€' : '$' }}{{ extractedData.item_price?.toFixed(2) }}
              <span :class="getConfidenceClass('item_price')">{{ getConfidenceIcon('item_price') }}</span>
            </span>
          </div>

          <div v-if="extractedData.shipping" class="flex justify-between items-center">
            <span class="text-sm text-gray-600">Shipping</span>
            <span class="font-medium flex items-center gap-1">
              {{ extractedData.currency === 'GBP' ? '£' : extractedData.currency === 'EUR' ? '€' : '$' }}{{ extractedData.shipping?.toFixed(2) }}
              <span :class="getConfidenceClass('shipping')">{{ getConfidenceIcon('shipping') }}</span>
            </span>
          </div>

          <div v-if="extractedData.purchase_date" class="flex justify-between items-center">
            <span class="text-sm text-gray-600">Purchase Date</span>
            <span class="font-medium flex items-center gap-1">
              {{ extractedData.purchase_date }}
              <span :class="getConfidenceClass('purchase_date')">{{ getConfidenceIcon('purchase_date') }}</span>
            </span>
          </div>

          <div v-if="extractedData.estimated_delivery" class="flex justify-between items-center">
            <span class="text-sm text-gray-600">Est. Delivery</span>
            <span class="font-medium flex items-center gap-1">
              {{ extractedData.estimated_delivery }}
              <span :class="getConfidenceClass('estimated_delivery')">{{ getConfidenceIcon('estimated_delivery') }}</span>
            </span>
          </div>

          <!-- Tracking Number (display only with copy) -->
          <div v-if="extractedData.tracking_number" class="flex justify-between items-center bg-gray-50 p-2 rounded">
            <span class="text-sm text-gray-600">Tracking</span>
            <div class="flex items-center gap-2">
              <code class="text-xs bg-gray-100 px-2 py-1 rounded">{{ extractedData.tracking_number }}</code>
              <button @click="copyTracking" class="text-blue-600 hover:text-blue-800 text-xs" title="Copy">
                📋
              </button>
            </div>
          </div>
        </div>

        <div class="text-xs text-gray-500">
          ✓ = High confidence | ⚠️ = Review recommended
        </div>

        <div class="flex justify-end gap-2 pt-2 border-t">
          <button @click="handleBack" class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">
            Back
          </button>
          <button
            @click="handleApply"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Apply to Form
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
```

---

## Task 5: Wire Into AcquireModal

### 5.1 Update AcquireModal.vue
**File:** `frontend/src/components/AcquireModal.vue`

Add imports and state:
```typescript
import PasteOrderModal from "./PasteOrderModal.vue";

const showPasteModal = ref(false);
```

Add handler:
```typescript
function handlePasteApply(data: any) {
  if (data.order_number) form.value.order_number = data.order_number;
  if (data.total_usd) form.value.purchase_price = data.total_usd;
  else if (data.total) form.value.purchase_price = data.total;
  if (data.purchase_date) form.value.purchase_date = data.purchase_date;
  if (data.estimated_delivery) form.value.estimated_delivery = data.estimated_delivery;
  showPasteModal.value = false;
}
```

Add button in template header:
```vue
<div class="p-4 border-b flex justify-between items-center">
  <h2 class="text-lg font-semibold">Acquire: {{ bookTitle }}</h2>
  <div class="flex items-center gap-2">
    <button
      @click="showPasteModal = true"
      class="text-sm text-blue-600 hover:text-blue-800"
    >
      📋 Paste Order
    </button>
    <button @click="emit('close')" class="text-gray-500 hover:text-gray-700">✕</button>
  </div>
</div>
```

Add modal component:
```vue
<PasteOrderModal
  v-if="showPasteModal"
  @close="showPasteModal = false"
  @apply="handlePasteApply"
/>
```

**Verification:** Click "Acquire" on a book, click "Paste Order", paste sample text, verify fields populate.

---

## Testing Checklist

- [ ] Admin config page loads at `/admin/config`
- [ ] Saving config persists across page refresh
- [ ] Non-admin users cannot access PUT `/admin/config`
- [ ] `POST /orders/extract` returns extracted fields
- [ ] Regex extracts eBay order number format
- [ ] GBP prices convert to USD using config rate
- [ ] LLM fallback triggers when confidence < 0.8
- [ ] PasteOrderModal shows input textarea initially
- [ ] Extract button calls API and shows results
- [ ] Confidence indicators show correctly
- [ ] Tracking number has copy button
- [ ] Apply populates AcquireModal fields
- [ ] Empty paste shows validation error
- [ ] Unextractable text shows helpful error

## Deployment

1. Run migration: `curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate`
2. Deploy backend with new endpoints
3. Deploy frontend with new components
4. Verify at staging before prod promotion
