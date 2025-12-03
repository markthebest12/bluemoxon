#!/bin/bash
#
# BlueMoxon Local Development Manager
#
# Usage:
#   ./scripts/dev.sh start     - Start all services (backend, frontend, optional postgres)
#   ./scripts/dev.sh stop      - Stop all services
#   ./scripts/dev.sh restart   - Restart all services
#   ./scripts/dev.sh status    - Show service status
#   ./scripts/dev.sh logs      - Tail all logs
#   ./scripts/dev.sh logs:be   - Tail backend logs only
#   ./scripts/dev.sh logs:fe   - Tail frontend logs only
#   ./scripts/dev.sh attach    - Attach to tmux session (Ctrl+B D to detach)
#   ./scripts/dev.sh clean     - Remove old logs (keeps last 7 days)
#
# Services:
#   - backend:  FastAPI on http://localhost:8000
#   - frontend: Vite on http://localhost:5173
#   - postgres: Optional, via docker-compose (use --with-db flag)
#
# Logs:
#   - Location: ~/.bluemoxon/logs/
#   - Auto-rotated daily, compressed after 1 day
#   - Auto-cleaned: logs older than 7 days removed
#
# Environment:
#   - BMX_LOG_DAYS: Days of logs to keep (default: 7)
#   - BMX_LOG_DIR: Custom log directory (default: ~/.bluemoxon/logs)
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_NAME="bluemoxon"
LOG_DIR="${BMX_LOG_DIR:-$HOME/.bluemoxon/logs}"
LOG_DAYS="${BMX_LOG_DAYS:-7}"
MAX_LOG_SIZE_MB=50  # Rotate logs larger than this

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Ensure log directory exists
ensure_log_dir() {
    mkdir -p "$LOG_DIR"
}

# Get today's log file path
get_log_file() {
    local service=$1
    local date=$(date +%Y-%m-%d)
    echo "$LOG_DIR/${service}-${date}.log"
}

# Rotate log if too large (inline rotation)
rotate_if_needed() {
    local log_file=$1
    if [[ -f "$log_file" ]]; then
        local size_mb=$(du -m "$log_file" 2>/dev/null | cut -f1)
        if [[ "$size_mb" -ge "$MAX_LOG_SIZE_MB" ]]; then
            local timestamp=$(date +%H%M%S)
            mv "$log_file" "${log_file%.log}-${timestamp}.log"
            gzip "${log_file%.log}-${timestamp}.log" 2>/dev/null &
        fi
    fi
}

# Clean old logs
clean_old_logs() {
    log_info "Cleaning logs older than $LOG_DAYS days..."
    find "$LOG_DIR" -name "*.log" -mtime +$LOG_DAYS -delete 2>/dev/null || true
    find "$LOG_DIR" -name "*.log.gz" -mtime +$LOG_DAYS -delete 2>/dev/null || true

    # Compress logs older than 1 day that aren't compressed
    find "$LOG_DIR" -name "*.log" -mtime +1 -exec gzip {} \; 2>/dev/null || true

    log_success "Log cleanup complete"
}

# Check if tmux session exists
session_exists() {
    tmux has-session -t "$SESSION_NAME" 2>/dev/null
}

# Check if a specific window exists
window_exists() {
    local window=$1
    tmux list-windows -t "$SESSION_NAME" 2>/dev/null | grep -q "^[0-9]*: $window"
}

# Start services
start_services() {
    local with_db=false

    # Parse flags
    for arg in "$@"; do
        case $arg in
            --with-db) with_db=true ;;
        esac
    done

    ensure_log_dir
    clean_old_logs

    if session_exists; then
        log_warn "Session '$SESSION_NAME' already exists. Use 'dev.sh stop' first or 'dev.sh attach' to view."
        return 1
    fi

    log_info "Starting BlueMoxon development services..."

    # Create new tmux session (detached)
    tmux new-session -d -s "$SESSION_NAME" -n "main"

    # Backend window
    local be_log=$(get_log_file "backend")
    rotate_if_needed "$be_log"
    tmux new-window -t "$SESSION_NAME" -n "backend"
    tmux send-keys -t "$SESSION_NAME:backend" "cd '$PROJECT_ROOT/backend'" Enter
    tmux send-keys -t "$SESSION_NAME:backend" "echo '=== Backend starting at $(date) ===' >> '$be_log'" Enter
    tmux send-keys -t "$SESSION_NAME:backend" "poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | tee -a '$be_log'" Enter
    log_success "Backend starting on http://localhost:8000"

    # Frontend window
    local fe_log=$(get_log_file "frontend")
    rotate_if_needed "$fe_log"
    tmux new-window -t "$SESSION_NAME" -n "frontend"
    tmux send-keys -t "$SESSION_NAME:frontend" "cd '$PROJECT_ROOT/frontend'" Enter
    tmux send-keys -t "$SESSION_NAME:frontend" "echo '=== Frontend starting at $(date) ===' >> '$fe_log'" Enter
    tmux send-keys -t "$SESSION_NAME:frontend" "npm run dev 2>&1 | tee -a '$fe_log'" Enter
    log_success "Frontend starting on http://localhost:5173"

    # Optional PostgreSQL via Docker
    if $with_db; then
        local db_log=$(get_log_file "postgres")
        rotate_if_needed "$db_log"
        tmux new-window -t "$SESSION_NAME" -n "postgres"
        tmux send-keys -t "$SESSION_NAME:postgres" "cd '$PROJECT_ROOT'" Enter
        tmux send-keys -t "$SESSION_NAME:postgres" "echo '=== PostgreSQL starting at $(date) ===' >> '$db_log'" Enter
        tmux send-keys -t "$SESSION_NAME:postgres" "docker-compose up postgres 2>&1 | tee -a '$db_log'" Enter
        log_success "PostgreSQL starting on localhost:5432"
    fi

    # Kill the initial empty window
    tmux kill-window -t "$SESSION_NAME:main" 2>/dev/null || true

    # Start background log rotation daemon (checks every hour)
    (
        while session_exists; do
            sleep 3600
            for service in backend frontend postgres; do
                rotate_if_needed "$(get_log_file "$service")"
            done
        done
    ) &>/dev/null &

    echo ""
    log_success "All services started in tmux session '$SESSION_NAME'"
    echo ""
    echo "  Logs:     $LOG_DIR/"
    echo "  Backend:  http://localhost:8000"
    echo "  Frontend: http://localhost:5173"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Commands:"
    echo "  ./scripts/dev.sh logs     - View all logs"
    echo "  ./scripts/dev.sh attach   - Attach to tmux (Ctrl+B D to detach)"
    echo "  ./scripts/dev.sh stop     - Stop all services"
}

# Stop services
stop_services() {
    if ! session_exists; then
        log_warn "No '$SESSION_NAME' session found"
        return 0
    fi

    log_info "Stopping BlueMoxon services..."

    # Send Ctrl+C to each window to gracefully stop processes
    for window in backend frontend postgres; do
        if tmux list-windows -t "$SESSION_NAME" 2>/dev/null | grep -q "$window"; then
            tmux send-keys -t "$SESSION_NAME:$window" C-c
            sleep 0.5
        fi
    done

    sleep 1

    # Kill the session
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

    log_success "All services stopped"
}

# Show status
show_status() {
    echo ""
    echo "BlueMoxon Development Status"
    echo "============================"
    echo ""

    if session_exists; then
        echo -e "tmux session: ${GREEN}running${NC}"
        echo ""
        echo "Windows:"
        tmux list-windows -t "$SESSION_NAME" 2>/dev/null | while read line; do
            echo "  $line"
        done
    else
        echo -e "tmux session: ${RED}not running${NC}"
    fi

    echo ""
    echo "Ports:"
    for port in 8000 5173 5432; do
        if lsof -i :$port >/dev/null 2>&1; then
            echo -e "  :$port ${GREEN}in use${NC}"
        else
            echo -e "  :$port ${YELLOW}free${NC}"
        fi
    done

    echo ""
    echo "Log directory: $LOG_DIR"
    if [[ -d "$LOG_DIR" ]]; then
        local log_size=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
        echo "  Size: $log_size"
        echo "  Files:"
        ls -lh "$LOG_DIR"/*.log "$LOG_DIR"/*.log.gz 2>/dev/null | tail -10 | while read line; do
            echo "    $line"
        done
    fi
    echo ""
}

# Tail logs
tail_logs() {
    local service=$1
    ensure_log_dir

    case $service in
        backend|be)
            tail -F "$LOG_DIR"/backend-*.log 2>/dev/null || log_warn "No backend logs found"
            ;;
        frontend|fe)
            tail -F "$LOG_DIR"/frontend-*.log 2>/dev/null || log_warn "No frontend logs found"
            ;;
        postgres|db)
            tail -F "$LOG_DIR"/postgres-*.log 2>/dev/null || log_warn "No postgres logs found"
            ;;
        *)
            # Tail all logs
            tail -F "$LOG_DIR"/*.log 2>/dev/null || log_warn "No logs found in $LOG_DIR"
            ;;
    esac
}

# Attach to tmux session
attach_session() {
    if ! session_exists; then
        log_error "No '$SESSION_NAME' session found. Run 'dev.sh start' first."
        return 1
    fi

    echo "Attaching to tmux session. Use Ctrl+B D to detach."
    tmux attach -t "$SESSION_NAME"
}

# Main
main() {
    local cmd=${1:-help}
    shift || true

    case $cmd in
        start)
            start_services "$@"
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_services "$@"
            ;;
        status)
            show_status
            ;;
        logs)
            tail_logs ""
            ;;
        logs:be|logs:backend)
            tail_logs backend
            ;;
        logs:fe|logs:frontend)
            tail_logs frontend
            ;;
        logs:db|logs:postgres)
            tail_logs postgres
            ;;
        attach)
            attach_session
            ;;
        clean)
            ensure_log_dir
            clean_old_logs
            ;;
        help|--help|-h)
            echo "BlueMoxon Local Development Manager"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  start [--with-db]  Start services (add --with-db for PostgreSQL)"
            echo "  stop               Stop all services"
            echo "  restart            Restart all services"
            echo "  status             Show service status"
            echo "  logs               Tail all logs"
            echo "  logs:be            Tail backend logs"
            echo "  logs:fe            Tail frontend logs"
            echo "  logs:db            Tail postgres logs"
            echo "  attach             Attach to tmux session"
            echo "  clean              Clean old logs"
            echo ""
            echo "Environment:"
            echo "  BMX_LOG_DIR   Log directory (default: ~/.bluemoxon/logs)"
            echo "  BMX_LOG_DAYS  Days to keep logs (default: 7)"
            echo ""
            echo "Examples:"
            echo "  $0 start              # Start backend + frontend"
            echo "  $0 start --with-db    # Start with PostgreSQL"
            echo "  $0 logs               # Watch all logs"
            echo "  $0 attach             # View tmux windows"
            ;;
        *)
            log_error "Unknown command: $cmd"
            echo "Run '$0 help' for usage"
            return 1
            ;;
    esac
}

main "$@"
