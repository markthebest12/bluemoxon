#!/bin/bash
# Update exchange rates from live data
# Uses frankfurter.app (free, no auth required)
# Run periodically: ./scripts/update-exchange-rates.sh [--prod]

set -e

# Check required dependencies
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is required but not installed."
        echo "Install with: $2"
        exit 1
    fi
}

check_dependency "jq" "brew install jq"
check_dependency "bc" "brew install bc (or use system bc)"
check_dependency "curl" "brew install curl"

# Parse arguments
ENV="staging"
if [[ "$1" == "--prod" ]]; then
    ENV="prod"
fi

# Check API key exists
KEY_FILE="$HOME/.bmx/${ENV}.key"
if [[ ! -f "$KEY_FILE" ]]; then
    echo "Error: API key not found at $KEY_FILE"
    echo ""
    echo "Setup required:"
    echo "  1. Get an API key from the admin"
    echo "  2. mkdir -p ~/.bmx"
    echo "  3. echo 'your-api-key' > ~/.bmx/${ENV}.key"
    echo "  4. chmod 600 ~/.bmx/${ENV}.key"
    exit 1
fi

echo "Fetching live exchange rates from frankfurter.app..."

# Fetch rates (USD as base)
RATES=$(curl -s --fail "https://api.frankfurter.app/latest?from=USD&to=GBP,EUR" 2>&1)

if [[ $? -ne 0 ]] || [[ -z "$RATES" ]]; then
    echo "Error: Failed to fetch rates from frankfurter.app"
    echo "Response: $RATES"
    exit 1
fi

# Extract rates (these are USD -> currency, we need currency -> USD)
USD_TO_GBP=$(echo "$RATES" | jq -r '.rates.GBP')
USD_TO_EUR=$(echo "$RATES" | jq -r '.rates.EUR')

if [[ "$USD_TO_GBP" == "null" ]] || [[ -z "$USD_TO_GBP" ]] || [[ "$USD_TO_EUR" == "null" ]] || [[ -z "$USD_TO_EUR" ]]; then
    echo "Error: Failed to parse rates from response"
    echo "Response: $RATES"
    exit 1
fi

# Invert rates (GBP -> USD = 1 / USD -> GBP)
GBP_TO_USD=$(echo "scale=4; 1 / $USD_TO_GBP" | bc)
EUR_TO_USD=$(echo "scale=4; 1 / $USD_TO_EUR" | bc)

if [[ -z "$GBP_TO_USD" ]] || [[ -z "$EUR_TO_USD" ]]; then
    echo "Error: Failed to calculate inverse rates"
    exit 1
fi

echo "Current rates:"
echo "  GBP -> USD: $GBP_TO_USD"
echo "  EUR -> USD: $EUR_TO_USD"
echo ""

# Update via API
echo "Updating $ENV environment..."

if [[ "$ENV" == "prod" ]]; then
    RESPONSE=$(bmx-api --prod PUT /admin/config "{\"gbp_to_usd_rate\": $GBP_TO_USD, \"eur_to_usd_rate\": $EUR_TO_USD}" 2>&1)
else
    RESPONSE=$(bmx-api PUT /admin/config "{\"gbp_to_usd_rate\": $GBP_TO_USD, \"eur_to_usd_rate\": $EUR_TO_USD}" 2>&1)
fi

# Check for API errors
if echo "$RESPONSE" | grep -qi "error\|unauthorized\|forbidden"; then
    echo "Error: API update failed"
    echo "Response: $RESPONSE"
    echo ""
    echo "Check that your API key at $KEY_FILE has admin permissions."
    exit 1
fi

echo "$RESPONSE"
echo ""
echo "Exchange rates updated successfully!"
