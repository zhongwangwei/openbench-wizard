#!/bin/bash
# -*- coding: utf-8 -*-
#
# OpenBench NML Wizard - X11 Launcher Script
#
# This script helps launch the GUI application over SSH X11 forwarding.
# Usage:
#   ./x11_launcher.sh              # Launch GUI
#   ./x11_launcher.sh --check      # Check X11 environment only
#   ./x11_launcher.sh --help       # Show help
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo "=============================================="
    echo "  OpenBench NML Wizard - X11 Launcher"
    echo "=============================================="
    echo
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_display() {
    echo "Checking DISPLAY environment..."

    if [ -z "$DISPLAY" ]; then
        print_error "DISPLAY environment variable is not set"
        echo
        echo "Solutions:"
        echo "  1. Connect with X11 forwarding:"
        echo "     ssh -X user@server"
        echo "     ssh -Y user@server  # if -X doesn't work"
        echo
        echo "  2. Set DISPLAY manually:"
        echo "     export DISPLAY=localhost:10.0"
        echo
        echo "  3. Use CLI mode instead:"
        echo "     python cli.py --interactive"
        return 1
    fi

    print_success "DISPLAY is set to: $DISPLAY"
    return 0
}

check_xauth() {
    echo "Checking X11 authentication..."

    if ! command -v xauth &> /dev/null; then
        print_warning "xauth not found (may still work)"
        return 0
    fi

    if xauth list 2>/dev/null | grep -q .; then
        print_success "X11 authentication configured"
        return 0
    else
        print_warning "No X11 authentication entries found"
        return 0
    fi
}

check_x11_connection() {
    echo "Testing X11 connection..."

    # Try to connect using xdpyinfo if available
    if command -v xdpyinfo &> /dev/null; then
        if xdpyinfo &> /dev/null; then
            print_success "X11 connection successful"
            return 0
        else
            print_error "Cannot connect to X11 display"
            return 1
        fi
    fi

    # Fallback: try xset
    if command -v xset &> /dev/null; then
        if xset q &> /dev/null; then
            print_success "X11 connection successful"
            return 0
        fi
    fi

    print_warning "Cannot verify X11 connection (no xdpyinfo/xset)"
    return 0
}

check_python() {
    echo "Checking Python environment..."

    if ! command -v $PYTHON &> /dev/null; then
        print_error "Python not found: $PYTHON"
        return 1
    fi

    PYTHON_VERSION=$($PYTHON --version 2>&1)
    print_success "Python found: $PYTHON_VERSION"

    # Check for PySide6
    if $PYTHON -c "import PySide6" 2>/dev/null; then
        print_success "PySide6 is installed"
        return 0
    else
        print_error "PySide6 is not installed"
        echo "  Install with: pip install PySide6"
        return 1
    fi
}

setup_x11_env() {
    echo "Setting up X11 environment variables..."

    # Optimize for X11 forwarding
    export QT_QUICK_BACKEND=software
    export LIBGL_ALWAYS_INDIRECT=1
    export QT_GRAPHICSSYSTEM=native

    # Disable OpenGL to avoid issues
    export QT_XCB_GL_INTEGRATION=none

    # Compression for slow connections
    export QT_XCB_FORCE_SOFTWARE_OPENGL=1

    print_success "X11 environment configured"
}

run_checks() {
    local errors=0

    check_display || ((errors++))
    check_xauth
    check_x11_connection || ((errors++))
    check_python || ((errors++))

    echo
    if [ $errors -eq 0 ]; then
        print_success "All checks passed!"
        return 0
    else
        print_error "$errors check(s) failed"
        return 1
    fi
}

show_help() {
    print_header
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --check     Check X11 environment without launching"
    echo "  --cli       Run CLI version instead of GUI"
    echo "  --help      Show this help message"
    echo
    echo "Examples:"
    echo "  # From local machine, launch on remote server:"
    echo "  ssh -X user@server 'cd /path/to/openbench_wizard && ./x11_launcher.sh'"
    echo
    echo "  # Check environment only:"
    echo "  ./x11_launcher.sh --check"
    echo
    echo "  # Use CLI mode (no X11 needed):"
    echo "  ./x11_launcher.sh --cli"
    echo
    echo "Environment variables:"
    echo "  PYTHON      Python interpreter to use (default: python3)"
    echo "  DISPLAY     X11 display (set by SSH -X automatically)"
    echo
    echo "Troubleshooting:"
    echo "  1. Ensure SSH X11 forwarding is enabled:"
    echo "     - Server: X11Forwarding yes in /etc/ssh/sshd_config"
    echo "     - Client: ForwardX11 yes in ~/.ssh/config"
    echo
    echo "  2. On macOS client, install XQuartz:"
    echo "     brew install --cask xquartz"
    echo
    echo "  3. On Windows client, install VcXsrv or Xming"
}

launch_gui() {
    print_header

    if ! run_checks; then
        echo
        print_error "Environment check failed. Fix issues above or use CLI mode:"
        echo "  python cli.py --interactive"
        exit 1
    fi

    echo
    echo "Launching OpenBench NML Wizard..."
    setup_x11_env

    cd "$SCRIPT_DIR"
    exec $PYTHON main.py "$@"
}

launch_cli() {
    print_header
    echo "Launching CLI mode..."
    cd "$SCRIPT_DIR"
    exec $PYTHON cli.py --interactive
}

# Main entry point
case "${1:-}" in
    --check)
        print_header
        run_checks
        ;;
    --cli)
        launch_cli
        ;;
    --help|-h)
        show_help
        ;;
    *)
        launch_gui "$@"
        ;;
esac
