#!/bin/bash
# =============================================================================
# BlueMoxon Capacity Monitor
# =============================================================================
# Real-time monitoring of key capacity metrics during load tests.
#
# Usage:
#   ./scripts/monitor-capacity.sh                    # Monitor only (staging)
#   ./scripts/monitor-capacity.sh --prod             # Monitor production
#   ./scripts/monitor-capacity.sh --generate 33,56   # Generate analyses for books
#   ./scripts/monitor-capacity.sh --generate 33,56,498 --prod  # Production
#
# Monitors:
#   - Lambda concurrent executions (API + Worker)
#   - Aurora database connections
#   - Bedrock invocation throttles
#   - Aurora ACU utilization
# =============================================================================

set -e

# Parse arguments
ENV="staging"
GENERATE_BOOKS=""
INTERVAL=5  # seconds between refreshes

while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            ENV="prod"
            shift
            ;;
        --generate)
            GENERATE_BOOKS="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--prod] [--generate BOOK_IDS] [--interval SECONDS]"
            echo ""
            echo "Options:"
            echo "  --prod              Monitor production (default: staging)"
            echo "  --generate IDS      Trigger analyses for comma-separated book IDs"
            echo "  --interval SECS     Refresh interval (default: 5)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set AWS profile based on environment
if [[ "$ENV" == "prod" ]]; then
    export AWS_PROFILE="bmx-prod"
    API_URL="https://api.bluemoxon.com"
    LAMBDA_API="bluemoxon-api"
    LAMBDA_WORKER="bluemoxon-analysis-worker"
    DB_ID="bluemoxon-db"
else
    export AWS_PROFILE="bmx-staging"
    API_URL="https://staging.api.bluemoxon.com"
    LAMBDA_API="bluemoxon-staging-api"
    LAMBDA_WORKER="bluemoxon-staging-analysis-worker"
    DB_ID="bluemoxon-staging-db"
fi

REGION="us-west-2"
API_KEY_FILE="$HOME/.bmx/${ENV}.key"

# Check API key exists
if [[ ! -f "$API_KEY_FILE" ]]; then
    echo "Error: API key not found at $API_KEY_FILE"
    exit 1
fi
API_KEY=$(cat "$API_KEY_FILE")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to get CloudWatch metric
get_metric() {
    local namespace="$1"
    local metric_name="$2"
    local dimensions="$3"
    local stat="${4:-Maximum}"
    local period="${5:-60}"

    aws cloudwatch get-metric-statistics \
        --namespace "$namespace" \
        --metric-name "$metric_name" \
        --dimensions $dimensions \
        --start-time "$(date -u -v-2M '+%Y-%m-%dT%H:%M:%SZ')" \
        --end-time "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        --period "$period" \
        --statistics "$stat" \
        --region "$REGION" \
        --output json 2>/dev/null | jq -r ".Datapoints | sort_by(.Timestamp) | last | .$stat // 0"
}

# Function to trigger analysis generation
trigger_analyses() {
    local book_ids="$1"
    echo -e "${CYAN}Triggering analyses for books: $book_ids${NC}"

    IFS=',' read -ra BOOKS <<< "$book_ids"
    for book_id in "${BOOKS[@]}"; do
        echo -n "  Book $book_id: "
        response=$(curl -s -X POST "${API_URL}/api/v1/books/${book_id}/analysis/generate-async" \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json")

        job_id=$(echo "$response" | jq -r '.job_id // empty')
        if [[ -n "$job_id" ]]; then
            echo -e "${GREEN}queued (job: ${job_id:0:8}...)${NC}"
        else
            error=$(echo "$response" | jq -r '.detail // "unknown error"')
            echo -e "${RED}failed: $error${NC}"
        fi
    done
    echo ""
}

# Function to display metrics
display_metrics() {
    clear
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         BlueMoxon Capacity Monitor - ${ENV^^}                  ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Last updated: $(date '+%H:%M:%S')  |  Refresh: ${INTERVAL}s  |  Ctrl+C to exit${NC}"
    echo ""

    # Lambda Metrics
    echo -e "${BOLD}┌─── Lambda ───────────────────────────────────────────────────┐${NC}"

    # API Lambda
    api_concurrent=$(get_metric "AWS/Lambda" "ConcurrentExecutions" "Name=FunctionName,Value=$LAMBDA_API")
    api_invocations=$(get_metric "AWS/Lambda" "Invocations" "Name=FunctionName,Value=$LAMBDA_API" "Sum")
    api_errors=$(get_metric "AWS/Lambda" "Errors" "Name=FunctionName,Value=$LAMBDA_API" "Sum")
    api_throttles=$(get_metric "AWS/Lambda" "Throttles" "Name=FunctionName,Value=$LAMBDA_API" "Sum")

    printf "│ %-20s Concurrent: ${BOLD}%3.0f${NC}  Invocations: %5.0f  Errors: %3.0f  Throttles: %3.0f │\n" \
        "API Lambda" "$api_concurrent" "$api_invocations" "$api_errors" "$api_throttles"

    # Worker Lambda
    worker_concurrent=$(get_metric "AWS/Lambda" "ConcurrentExecutions" "Name=FunctionName,Value=$LAMBDA_WORKER")
    worker_invocations=$(get_metric "AWS/Lambda" "Invocations" "Name=FunctionName,Value=$LAMBDA_WORKER" "Sum")
    worker_errors=$(get_metric "AWS/Lambda" "Errors" "Name=FunctionName,Value=$LAMBDA_WORKER" "Sum")
    worker_throttles=$(get_metric "AWS/Lambda" "Throttles" "Name=FunctionName,Value=$LAMBDA_WORKER" "Sum")

    printf "│ %-20s Concurrent: ${BOLD}%3.0f${NC}  Invocations: %5.0f  Errors: %3.0f  Throttles: %3.0f │\n" \
        "Analysis Worker" "$worker_concurrent" "$worker_invocations" "$worker_errors" "$worker_throttles"

    echo -e "${BOLD}└──────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Database Metrics
    echo -e "${BOLD}┌─── Aurora Database ──────────────────────────────────────────┐${NC}"

    db_connections=$(get_metric "AWS/RDS" "DatabaseConnections" "Name=DBClusterIdentifier,Value=$DB_ID" "Maximum")
    db_cpu=$(get_metric "AWS/RDS" "CPUUtilization" "Name=DBClusterIdentifier,Value=$DB_ID" "Average")
    db_acu=$(get_metric "AWS/RDS" "ACUUtilization" "Name=DBClusterIdentifier,Value=$DB_ID" "Average")

    # Color code based on thresholds
    if (( $(echo "$db_connections > 50" | bc -l) )); then
        conn_color=$RED
    elif (( $(echo "$db_connections > 20" | bc -l) )); then
        conn_color=$YELLOW
    else
        conn_color=$GREEN
    fi

    if (( $(echo "$db_cpu > 80" | bc -l) )); then
        cpu_color=$RED
    elif (( $(echo "$db_cpu > 50" | bc -l) )); then
        cpu_color=$YELLOW
    else
        cpu_color=$GREEN
    fi

    printf "│ Connections: ${conn_color}${BOLD}%3.0f${NC}     CPU: ${cpu_color}%5.1f%%${NC}     ACU Utilization: %5.1f%%         │\n" \
        "$db_connections" "$db_cpu" "$db_acu"

    echo -e "${BOLD}└──────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Bedrock Metrics
    echo -e "${BOLD}┌─── Bedrock AI ───────────────────────────────────────────────┐${NC}"

    # Note: Bedrock metrics use different namespace
    bedrock_invocations=$(get_metric "AWS/Bedrock" "Invocations" "Name=ModelId,Value=us.anthropic.claude-sonnet-4-5-20250929-v1:0" "Sum")
    bedrock_throttles=$(get_metric "AWS/Bedrock" "InvocationThrottles" "Name=ModelId,Value=us.anthropic.claude-sonnet-4-5-20250929-v1:0" "Sum")
    bedrock_latency=$(get_metric "AWS/Bedrock" "InvocationLatency" "Name=ModelId,Value=us.anthropic.claude-sonnet-4-5-20250929-v1:0" "Average")

    if (( $(echo "$bedrock_throttles > 0" | bc -l) )); then
        throttle_color=$RED
    else
        throttle_color=$GREEN
    fi

    printf "│ Invocations (2min): ${BOLD}%3.0f${NC}  Throttles: ${throttle_color}${BOLD}%3.0f${NC}  Latency: %6.0f ms       │\n" \
        "$bedrock_invocations" "$bedrock_throttles" "$bedrock_latency"

    echo -e "${BOLD}└──────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Active Analysis Jobs
    echo -e "${BOLD}┌─── Analysis Jobs ────────────────────────────────────────────┐${NC}"

    # Get books with analysis job status
    books_response=$(curl -s "${API_URL}/api/v1/books?limit=100" \
        -H "X-API-Key: $API_KEY" 2>/dev/null || echo '{"items":[]}')

    # Extract pending and running book IDs
    pending_ids=$(echo "$books_response" | jq -r '.items[] | select(.analysis_job_status == "pending") | .id' 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    running_ids=$(echo "$books_response" | jq -r '.items[] | select(.analysis_job_status == "running") | .id' 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    pending_count=$(echo "$books_response" | jq '[.items[] | select(.analysis_job_status == "pending")] | length' 2>/dev/null || echo "0")
    running_count=$(echo "$books_response" | jq '[.items[] | select(.analysis_job_status == "running")] | length' 2>/dev/null || echo "0")

    # Color code
    if (( running_count > 0 )); then
        running_color=$GREEN
    else
        running_color=$NC
    fi
    if (( pending_count > 0 )); then
        pending_color=$YELLOW
    else
        pending_color=$NC
    fi

    printf "│ Pending: ${pending_color}${BOLD}%2s${NC} %-18s Running: ${running_color}${BOLD}%2s${NC} %-15s │\n" \
        "$pending_count" "[${pending_ids:-none}]" "$running_count" "[${running_ids:-none}]"

    echo -e "${BOLD}└──────────────────────────────────────────────────────────────┘${NC}"
}

# Main execution
echo -e "${BOLD}BlueMoxon Capacity Monitor${NC}"
echo "Environment: $ENV"
echo "AWS Profile: $AWS_PROFILE"
echo ""

# Verify AWS credentials
if ! aws sts get-caller-identity --query 'Account' --output text >/dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials not valid for profile $AWS_PROFILE${NC}"
    exit 1
fi

# Trigger analyses if requested
if [[ -n "$GENERATE_BOOKS" ]]; then
    trigger_analyses "$GENERATE_BOOKS"
    echo "Starting monitoring in 3 seconds..."
    sleep 3
fi

# Main monitoring loop
while true; do
    display_metrics
    sleep "$INTERVAL"
done
