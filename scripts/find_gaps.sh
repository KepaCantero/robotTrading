#!/bin/bash
# Find files with GAP violations and generate task list

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKS_DIR="$REPO_ROOT/.tasks"
SUMMARY_FILE="$REPO_ROOT/GAP_AUDIT_SUMMARY.md"

echo "🔍 GAP Audit Tool"
echo "Repository: $REPO_ROOT"
echo ""

# Find all requirements files with GAP violations
echo "Scanning for GAP violations..."

# Use grep to find files with GAP violations
mapfile -t gap_files < <(grep -r -l "GAP" "$REPO_ROOT/.requirements" --include="*.md" 2>/dev/null || true)

if [ ${#gap_files[@]} -eq 0 ]; then
    echo "✅ No GAP violations found!"
    exit 0
fi

echo "Found ${#gap_files[@]} files with GAP violations"
echo ""

# Create summary
{
    echo "# GAP Audit Summary Report"
    echo ""
    echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Repository: $REPO_ROOT"
    echo ""
    echo "## Summary"
    echo ""
    echo "| Metric | Count |"
    echo "|--------|-------|"
    echo "| Files with GAPs | ${#gap_files[@]} |"
    echo ""
    echo "## Files with GAP Violations"
    echo ""
} > "$SUMMARY_FILE"

# Process each file
priority_p0=0
priority_p1=0
priority_p2=0
priority_p3=0

for req_file in "${gap_files[@]}"; do
    # Extract GAP violations
    grep "GAP" "$req_file" | while read -r line; do
        # Extract rule ID and description
        rule_id=$(echo "$line" | grep -oE '[A-Z]+-[0-9]+' | head -1)
        description=$(echo "$line" | sed -E 's/.*GAP[[:space:]]*-?[[:space:]]*(.*)/\1/' | sed 's/|[[:space:]]*$//')

        # Determine priority
        priority="P3"  # Default
        case "$rule_id" in
            TRD-001|TRD-005|SEC-001|SEC-002|SEC-003|CC-006)
                priority="P0"
                ;;
            LOG-004|LOG-001|TRD-004|TRD-007|SEC-007)
                priority="P1"
                ;;
            TYP-001|TYP-003|ARCH-004|ARCH-006|CC-001|CC-002)
                priority="P2"
                ;;
        esac

        # Get Python file path
        python_path="${req_file#$REPO_ROOT/.requirements/}"
        python_path="${python_path%.requirements.md}.py"

        # Get layer
        layer="L0_Other"
        case "$python_path" in
            *market_microstructure*) layer="L1_Microstructure" ;;
            *ensemble*) layer="L2_Ensemble" ;;
            *backtesting/core*) layer="L3_Backtesting_Core" ;;
            *backtesting/labeling*) layer="L4_Backtesting_Labeling" ;;
            *backtesting/validation*) layer="L5_Backtesting_Validation" ;;
            *domain/services*|*domain/strategies*) layer="L6_Domain_Services" ;;
            *domain/entities*|*domain/value_objects*) layer="L7_Domain_Entities" ;;
            *application*) layer="L8_Application" ;;
            *core*) layer="L9_Core" ;;
            *database*|*repositories*) layer="L10_Data" ;;
        esac

        # Add to summary
        echo "- \`$python_path\` - **$rule_id**: $description ($priority)" >> "$SUMMARY_FILE"

        # Count priorities
        case "$priority" in
            P0) ((priority_p0++)) ;;
            P1) ((priority_p1++)) ;;
            P2) ((priority_p2++)) ;;
            P3) ((priority_p3++)) ;;
        esac
    done
done

# Add priority summary to summary file
{
    echo ""
    echo "## Summary by Priority"
    echo ""
    echo "| Priority | Count |"
    echo "|----------|-------|"
    echo "| P0 (Critical) | $priority_p0 |"
    echo "| P1 (High) | $priority_p1 |"
    echo "| P2 (Medium) | $priority_p2 |"
    echo "| P3 (Low) | $priority_p3 |"
    echo ""
    echo "## Next Steps"
    echo ""
    echo "1. Call @agent-tech-lead-orchestrator with this summary"
    echo "2. The orchestrator will coordinate the workflow:"
    echo "   - @agent-requirement-expert (if requirements missing)"
    echo "   - @agent-python-expert (to implement fixes)"
    echo "   - @agent-python-testing-expert (to create tests)"
    echo "   - @agent-code-reviewer (to review and QA)"
    echo "   - @agent-code-auditor (to audit requirements compliance)"
    echo ""
} >> "$SUMMARY_FILE"

# Print summary
echo "Summary by Priority:"
echo "  P0 (Critical): $priority_p0"
echo "  P1 (High):     $priority_p1"
echo "  P2 (Medium):   $priority_p2"
echo "  P3 (Low):      $priority_p3"
echo ""
echo "Summary report: $SUMMARY_FILE"
echo ""
echo "Next: Call @agent-tech-lead-orchestrator to process the workflow"
