#!/bin/bash
# Update exchange rates from live data
# Uses frankfurter.app (free, no auth required)
# Run periodically: ./scripts/update-exchange-rates.sh [--prod]

set -e

ENV="staging"
if [[ "$1" == "--prod" ]]; then
    ENV="prod"
fi

echo "Fetching live exchange rates..."

# Fetch rates (USD as base)
RATES=$(curl -s "https://api.frankfurter.app/latest?from=USD&to=GBP,EUR")

if [[ -z "$RATES" ]]; then
    echo "Error: Failed to fetch rates"
    exit 1
fi

# Extract rates (these are USD -> currency, we need currency -> USD)
USD_TO_GBP=$(echo "$RATES" | jq -r '.rates.GBP')
USD_TO_EUR=$(echo "$RATES" | jq -r '.rates.EUR')

if [[ "$USD_TO_GBP" == "null" ]] || [[ "$USD_TO_EUR" == "null" ]]; then
    echo "Error: Failed to parse rates"
    echo "Response: $RATES"
    exit 1
fi

# Invert rates (GBP -> USD = 1 / USD -> GBP)
GBP_TO_USD=$(echo "scale=4; 1 / $USD_TO_GBP" | bc)
EUR_TO_USD=$(echo "scale=4; 1 / $USD_TO_EUR" | bc)

echo "Current rates:"
echo "  GBP -> USD: $GBP_TO_USD"
echo "  EUR -> USD: $EUR_TO_USD"

# Update via API
echo ""
echo "Updating $ENV environment..."

if [[ "$ENV" == "prod" ]]; then
    bmx-api --prod PUT /admin/config "{\"gbp_to_usd_rate\": $GBP_TO_USD, \"eur_to_usd_rate\": $EUR_TO_USD}"
else
    bmx-api PUT /admin/config "{\"gbp_to_usd_rate\": $GBP_TO_USD, \"eur_to_usd_rate\": $EUR_TO_USD}"
fi

echo ""
echo "Exchange rates updated successfully!"
