#!/bin/bash
# run_all.sh — Solve all graph instances in a directory and print timing summary.
#
# Usage:  ./run_all.sh <directory>
# Example: ./run_all.sh instances/

set -uo pipefail

DIR="${1:?Usage: $0 <directory>}"
SOLVER="$(cd "$(dirname "$0")" && pwd)/branching.py"
PYTHON="${PYTHON:-python3}"

if [ ! -d "$DIR" ]; then
    echo "Error: '$DIR' is not a directory"
    exit 1
fi

# Collect all .grl and .gr files
FILES=()
for f in "$DIR"/*.grl "$DIR"/*.gr; do
    [ -e "$f" ] && FILES+=("$f")
done

if [ ${#FILES[@]} -eq 0 ]; then
    echo "No .grl or .gr files found in '$DIR'"
    exit 1
fi

echo "============================================"
echo "  Solving ${#FILES[@]} instance(s) in: $DIR"
echo "============================================"
echo ""

PASS=0
FAIL=0
TOTAL_TIME=0
declare -a RESULTS

for f in "${FILES[@]}"; do
    NAME="$(basename "$f")"
    echo "--- $NAME ---"

    START=$(date +%s%N)
    OUTPUT=$($PYTHON "$SOLVER" "$f" 2>&1) && STATUS="PASS" || STATUS="FAIL"
    END=$(date +%s%N)

    ELAPSED=$(printf "%.3f" "$(echo "scale=6; ($END - $START) / 1000000000" | bc)")
    TOTAL_TIME=$(printf "%.3f" "$(echo "$TOTAL_TIME + $ELAPSED" | bc)")

    echo "$OUTPUT"
    echo ""
    echo "  Time: ${ELAPSED}s  [$STATUS]"
    echo ""

    RESULTS+=("$STATUS  ${ELAPSED}s  $NAME")

    if [ "$STATUS" = "PASS" ]; then
        ((PASS++))
    else
        ((FAIL++))
    fi
done

echo ""
echo "============================================"
echo "  SUMMARY"
echo "============================================"
echo ""
printf "  %-6s  %-10s  %s\n" "Status" "Time" "Instance"
printf "  %-6s  %-10s  %s\n" "------" "----------" "--------"
for r in "${RESULTS[@]}"; do
    printf "  %-6s  %-10s  %s\n" $r
done
echo ""
echo "  Passed: $PASS / $((PASS + FAIL))"
echo "  Failed: $FAIL / $((PASS + FAIL))"
echo "  Total time: ${TOTAL_TIME}s"
echo "============================================"
