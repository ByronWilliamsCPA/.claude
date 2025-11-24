#!/bin/bash
# Test Runner for Claude Code Configuration Scripts
# Runs BATS tests and generates coverage report

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*"; }

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       Claude Code Configuration - Test Suite               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

check_bats() {
    if ! command -v bats &> /dev/null; then
        log_warn "BATS not found. Installing..."
        if command -v npm &> /dev/null; then
            npm install -g bats
        elif command -v brew &> /dev/null; then
            brew install bats-core
        elif command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y bats
        else
            log_error "Cannot install BATS automatically. Please install manually:"
            echo "  npm install -g bats"
            echo "  # or"
            echo "  brew install bats-core"
            echo "  # or"
            echo "  apt-get install bats"
            exit 1
        fi
    fi
    log_success "BATS found: $(bats --version)"
}

run_tests() {
    local test_file="${1:-}"
    local verbose="${2:-0}"

    cd "$SCRIPT_DIR"

    if [ -n "$test_file" ]; then
        log_info "Running tests from: $test_file"
        if [ "$verbose" = "1" ]; then
            bats -t "$test_file"
        else
            bats "$test_file"
        fi
    else
        log_info "Running all tests..."
        local test_files=$(find . -name "test_*.bats" -type f | sort)

        if [ -z "$test_files" ]; then
            log_error "No test files found!"
            exit 1
        fi

        local total_tests=0
        local passed_tests=0
        local failed_tests=0
        local skipped_tests=0

        for file in $test_files; do
            echo ""
            log_info "Testing: $(basename "$file" .bats)"
            echo "────────────────────────────────────────────────"

            if [ "$verbose" = "1" ]; then
                if bats -t "$file"; then
                    ((passed_tests++)) || true
                else
                    ((failed_tests++)) || true
                fi
            else
                if bats "$file"; then
                    ((passed_tests++)) || true
                else
                    ((failed_tests++)) || true
                fi
            fi
            ((total_tests++)) || true
        done

        echo ""
        echo "════════════════════════════════════════════════"
        echo "Test Summary"
        echo "════════════════════════════════════════════════"
        echo "Total test files: $total_tests"
        echo "Passed: $passed_tests"
        echo "Failed: $failed_tests"
        echo ""

        if [ "$failed_tests" -gt 0 ]; then
            log_error "Some tests failed!"
            return 1
        else
            log_success "All tests passed!"
            return 0
        fi
    fi
}

generate_coverage_report() {
    log_info "Generating coverage report..."

    # Scripts to analyze
    local scripts=(
        "install.sh"
        "mcp-manager.sh"
        "setup-env.sh"
        "setup-project-mcp.sh"
        "validate-mcp-env.sh"
        "update.sh"
        "start-claude.sh"
    )

    local total_lines=0
    local total_functions=0
    local tested_functions=0

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                   Coverage Report                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    printf "%-25s %10s %12s %12s\n" "Script" "Lines" "Functions" "Tests"
    echo "─────────────────────────────────────────────────────────────"

    for script in "${scripts[@]}"; do
        local script_path="$PROJECT_ROOT/scripts/$script"
        local test_file="$SCRIPT_DIR/test_$(echo "$script" | sed 's/\.sh$//' | sed 's/-/_/g').bats"

        if [ -f "$script_path" ]; then
            local lines
            lines=$(wc -l < "$script_path" | tr -d ' ')
            local functions
            functions=$(grep -cE "^[a-z_]+\(\)|^[a-z_]+ \(\)" "$script_path" 2>/dev/null) || functions=0
            local tests=0

            if [ -f "$test_file" ]; then
                tests=$(grep -c "^@test" "$test_file" 2>/dev/null) || tests=0
            fi

            printf "%-25s %10s %12s %12s\n" "$script" "$lines" "$functions" "$tests"

            ((total_lines += lines)) || true
            ((total_functions += functions)) || true
            ((tested_functions += tests)) || true
        fi
    done

    echo "─────────────────────────────────────────────────────────────"
    printf "%-25s %10d %12d %12d\n" "TOTAL" "$total_lines" "$total_functions" "$tested_functions"
    echo ""

    # Calculate coverage percentage based on test count vs functions
    local coverage=0
    if [ "$total_functions" -gt 0 ]; then
        coverage=$((tested_functions * 100 / total_functions))
        # Cap at 100% since we have more tests than functions
        if [ "$coverage" -gt 100 ]; then
            coverage=100
        fi
    fi

    echo "═══════════════════════════════════════════════════════════"
    echo ""
    if [ "$coverage" -ge 90 ]; then
        log_success "Coverage: ${coverage}% (Target: 90%)"
    elif [ "$coverage" -ge 80 ]; then
        log_warn "Coverage: ${coverage}% (Target: 90%)"
    else
        log_error "Coverage: ${coverage}% (Target: 90%)"
    fi
    echo ""

    # Detailed test count per file
    echo "Test Distribution:"
    echo "─────────────────────────────────────────────────────────────"
    for script in "${scripts[@]}"; do
        local test_file="$SCRIPT_DIR/test_$(echo "$script" | sed 's/\.sh$//' | sed 's/-/_/g').bats"
        if [ -f "$test_file" ]; then
            local test_count=$(grep -c "^@test" "$test_file" 2>/dev/null || echo "0")
            printf "  %-40s %d tests\n" "$(basename "$test_file")" "$test_count"
        fi
    done
    echo ""
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST_FILE]

Options:
  -v, --verbose     Run tests in verbose mode (show timing)
  -c, --coverage    Generate coverage report
  -h, --help        Show this help message

Examples:
  $0                    # Run all tests
  $0 -v                 # Run all tests verbosely
  $0 test_install.bats  # Run specific test file
  $0 -c                 # Generate coverage report only
  $0 -v -c              # Run tests verbosely and show coverage

EOF
}

main() {
    local verbose=0
    local coverage_only=0
    local test_file=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                verbose=1
                shift
                ;;
            -c|--coverage)
                coverage_only=1
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *.bats)
                test_file="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    print_header

    if [ "$coverage_only" = "1" ] && [ -z "$test_file" ]; then
        generate_coverage_report
        exit 0
    fi

    check_bats

    if run_tests "$test_file" "$verbose"; then
        generate_coverage_report
        exit 0
    else
        generate_coverage_report
        exit 1
    fi
}

main "$@"
