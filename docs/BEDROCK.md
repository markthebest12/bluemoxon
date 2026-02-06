# AWS Bedrock Integration

## Overview

BlueMoxon uses AWS Bedrock to generate Napoleon framework analyses for antiquarian books. The service sends book metadata and images to Claude models and receives comprehensive valuations.

## Model Configuration

**Current Models (as of 2025-12-12):**

| Name | Model ID | Use Case |
|------|----------|----------|
| Sonnet | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Fast analysis (~20-30s) |
| Opus | `us.anthropic.claude-opus-4-5-20251101-v1:0` | High-quality analysis (~40-60s) |

Models are configured in `backend/app/services/bedrock.py`.

## AWS CLI Examples

### Simple Text Request

```bash
# Create test payload
echo '{"anthropic_version":"bedrock-2023-05-31","max_tokens":500,"messages":[{"role":"user","content":"What is 2+2?"}]}' > .tmp/test.json

# Invoke Claude Sonnet
aws bedrock-runtime invoke-model \
  --model-id "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
  --body file://.tmp/test.json \
  --content-type application/json \
  --accept application/json \
  --cli-binary-format raw-in-base64-out \
  .tmp/response.json \
  --region us-west-2

# View response
cat .tmp/response.json | jq '.content[0].text'
```

### With System Prompt

```bash
# Create payload with system prompt
cat > .tmp/system-test.json << 'EOF'
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 4000,
  "system": "You are an expert antiquarian book appraiser. Provide detailed valuations.",
  "messages": [{
    "role": "user",
    "content": "What factors affect the value of a first edition Victorian book?"
  }]
}
EOF

# Invoke
aws bedrock-runtime invoke-model \
  --model-id "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
  --body file://.tmp/system-test.json \
  --content-type application/json \
  --accept application/json \
  --cli-binary-format raw-in-base64-out \
  .tmp/response.json \
  --region us-west-2
```

### With Image (Vision)

```python
# Python script to create image payload
import json
import base64

# Load image
with open('book-image.jpg', 'rb') as f:
    image_b64 = base64.b64encode(f.read()).decode('utf-8')

payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 4000,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this book binding."},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64
                }
            }
        ]
    }]
}

with open('.tmp/image-test.json', 'w') as f:
    json.dump(payload, f)
```

```bash
# Invoke with image
aws bedrock-runtime invoke-model \
  --model-id "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
  --body file://.tmp/image-test.json \
  --content-type application/json \
  --accept application/json \
  --cli-binary-format raw-in-base64-out \
  .tmp/response.json \
  --region us-west-2
```

### Full Napoleon Framework Analysis

```python
import json
import base64
import boto3

# Load Napoleon prompt from S3
s3 = boto3.client('s3', region_name='us-west-2')
response = s3.get_object(Bucket='bluemoxon-images', Key='prompts/napoleon-framework/v3.md')
system_prompt = response['Body'].read().decode('utf-8')

# Load book images (up to 10)
images = []
for i in range(1, 11):
    try:
        with open(f'book-image-{i}.jpg', 'rb') as f:
            images.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(f.read()).decode('utf-8')
                }
            })
    except FileNotFoundError:
        break

# Build payload
content = [
    {
        "type": "text",
        "text": """Analyze this book for the collection:

## Book Metadata
- Title: Idylls of the King
- Author: Alfred Lord Tennyson
- Publisher: Edward Moxon (Tier: TIER_1)
- Publication Date: 1859
- Binding Type: Full Morocco
- Binder: Zaehnsdorf (authenticated)

## Images
{} images attached below.""".format(len(images))
    }
] + images

payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 16000,
    "system": system_prompt,
    "messages": [{"role": "user", "content": content}]
}

with open('.tmp/napoleon-test.json', 'w') as f:
    json.dump(payload, f)

print(f"Payload size: {len(json.dumps(payload)) / 1024:.1f} KB")
```

## API Usage

### Generate Analysis via API

```bash
# Using bmx-api (staging)
bmx-api POST /books/123/analysis/generate

# Using bmx-api (production)
bmx-api --prod POST /books/123/analysis/generate

# With specific model
bmx-api POST "/books/123/analysis/generate?model=opus"

# Using curl directly
curl -X POST "https://api.bluemoxon.com/api/v1/books/123/analysis/generate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json"
```

## Performance Benchmarks

| Scenario | Claude Sonnet | Claude Opus |
|----------|------------------|-----------------|
| Text only (no images) | ~5-10s | ~15-20s |
| 1 image (~100KB) | ~15-20s | ~30-40s |
| 5 images (~500KB) | ~20-25s | ~40-50s |
| 10 images (~2MB) | ~25-35s | ~50-70s |

## Troubleshooting

### Timeout Issues

If Claude requests hang indefinitely:

1. **Check Marketplace approval** - New models require AWS Marketplace approval
2. **Wait 24-48 hours** - Provisioning may take time after approval
3. **Test via CLI first** - Isolate Lambda from the equation
4. **Check IAM permissions** - Ensure inference profile access

### IAM Policy for Cross-Region Inference Profiles

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:inference-profile/*",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    }
  ]
}
```

### Response Token Limits

- Default `max_tokens`: 16000 (sufficient for Napoleon framework)
- Claude output limit: ~8000 tokens typical
- If truncated, increase `max_tokens` or simplify prompt

## Related Files

- `backend/app/services/bedrock.py` - Bedrock client and invocation logic
- `backend/app/api/v1/books.py` - Analysis generation endpoint
- `s3://bluemoxon-images/prompts/napoleon-framework/v3.md` - Napoleon Framework system prompt
- `backend/prompts/napoleon-framework/v3.md` - Source file (deploy to S3 after changes)
