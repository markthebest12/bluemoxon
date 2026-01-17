#!/bin/bash
# Fetch BMX API key from Secrets Manager at session start

SECRET=$(aws secretsmanager get-secret-value \
    --secret-id bluemoxon-prod/api-key \
    --query SecretString \
    --output text 2>/dev/null)

if [[ -n "$SECRET" && -n "$CLAUDE_ENV_FILE" ]]; then
    KEY=$(echo "$SECRET" | jq -r '.key')
    echo "export BLUEMOXON_API_KEY=\"$KEY\"" >> "$CLAUDE_ENV_FILE"
    echo "export BMX_PROD_KEY=\"$KEY\"" >> "$CLAUDE_ENV_FILE"
fi

exit 0
