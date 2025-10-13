#!/bin/bash
# EZRealtor.app System Management Script

set -e

SERVICE_NAME="ezrealtor"
SERVICE_FILE="/root/ezrealtor/ezadmin/systemd/ezrealtor.service"
SYSTEM_SERVICE="/etc/systemd/system/ezrealtor.service"
PROJECT_DIR="/root/ezrealtor/ezadmin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to install the service
install_service() {
    print_status "Installing EZRealtor systemd service..."
    
    # Copy service file to systemd directory
    sudo cp "$SERVICE_FILE" "$SYSTEM_SERVICE"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable the service
    sudo systemctl enable "$SERVICE_NAME"
    
    print_success "Service installed and enabled"
}

# Function to uninstall the service
uninstall_service() {
    print_status "Uninstalling EZRealtor systemd service..."
    
    # Stop the service if running
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Disable the service
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    
    # Remove service file
    sudo rm -f "$SYSTEM_SERVICE"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    print_success "Service uninstalled"
}

# Function to start the service
start_service() {
    print_status "Starting EZRealtor service..."
    sudo systemctl start "$SERVICE_NAME"
    print_success "Service started"
}

# Function to stop the service
stop_service() {
    print_status "Stopping EZRealtor service..."
    sudo systemctl stop "$SERVICE_NAME"
    print_success "Service stopped"
}

# Function to restart the service
restart_service() {
    print_status "Restarting EZRealtor service..."
    sudo systemctl restart "$SERVICE_NAME"
    print_success "Service restarted"
}

# Function to reload the service
reload_service() {
    print_status "Reloading EZRealtor service..."
    sudo systemctl reload "$SERVICE_NAME"
    print_success "Service reloaded"
}

# Function to check service status
status_service() {
    print_status "EZRealtor service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager
}

# Function to show service logs
logs_service() {
    local lines=${1:-50}
    print_status "EZRealtor service logs (last $lines lines):"
    sudo journalctl -u "$SERVICE_NAME" -n "$lines" --no-pager
}

# Function to follow service logs
follow_logs() {
    print_status "Following EZRealtor service logs (Ctrl+C to exit):"
    sudo journalctl -u "$SERVICE_NAME" -f
}

# Function to enable service
enable_service() {
    print_status "Enabling EZRealtor service..."
    sudo systemctl enable "$SERVICE_NAME"
    print_success "Service enabled (will start on boot)"
}

# Function to disable service
disable_service() {
    print_status "Disabling EZRealtor service..."
    sudo systemctl disable "$SERVICE_NAME"
    print_success "Service disabled (will not start on boot)"
}

# Function to show help
show_help() {
    echo "EZRealtor.app System Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  install     Install the systemd service"
    echo "  uninstall   Uninstall the systemd service"
    echo "  start       Start the service"
    echo "  stop        Stop the service"
    echo "  restart     Restart the service"
    echo "  reload      Reload the service"
    echo "  status      Show service status"
    echo "  logs [N]    Show last N lines of logs (default: 50)"
    echo "  follow      Follow logs in real-time"
    echo "  enable      Enable service (start on boot)"
    echo "  disable     Disable service (don't start on boot)"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install          # Install and enable the service"
    echo "  $0 start            # Start the service"
    echo "  $0 logs 100         # Show last 100 log lines"
    echo "  $0 follow           # Follow logs in real-time"
}

# Main script logic
case "${1:-}" in
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    reload)
        reload_service
        ;;
    status)
        status_service
        ;;
    logs)
        logs_service "${2:-50}"
        ;;
    follow)
        follow_logs
        ;;
    enable)
        enable_service
        ;;
    disable)
        disable_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac