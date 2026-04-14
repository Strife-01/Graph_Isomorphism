#!/bin/bash
# run_zip.sh — Unzip password-protected instance zips one by one, solve, and print timing summary.
#
# Usage:  ./run_zip.sh <zipfile>
# Example: ./run_zip.sh bonus_instances.zip
#
# The outer zip may itself be password-protected (prompts once).
# Each inner zip is password-protected and you are prompted for the
# password right before extracting and solving it.

set -uo pipefail

ZIPFILE="${1:?Usage: $0 <zipfile>}"
SOLVER="$(cd "$(dirname "$0")" && pwd)/branching.py"
PYTHON="${PYTHON:-python3}"
WORKDIR=$(mktemp -d)

trap "rm -rf '$WORKDIR'" EXIT

if [ ! -f "$ZIPFILE" ]; then
    echo "Error: '$ZIPFILE' not found"
    exit 1
fi

echo "============================================"
echo "  Extracting outer zip: $(basename "$ZIPFILE")"
echo "============================================"
echo ""

# Try extracting without password first; if it fails, ask for one
if ! unzip -q -o "$ZIPFILE" -d "$WORKDIR" 2>/dev/null; then
    read -rsp "Password for $(basename "$ZIPFILE"): " OUTER_PASS
    echo ""
    unzip -q -o -P "$OUTER_PASS" "$ZIPFILE" -d "$WORKDIR"
fi

# Find inner zips and plain graph files
INNER_ZIPS=()
PLAIN_FILES=()
for f in "$WORKDIR"/*.zip; do
    [ -e "$f" ] && INNER_ZIPS+=("$f")
done
for f in "$WORKDIR"/*.grl "$WORKDIR"/*.gr; do
    [ -e "$f" ] && PLAIN_FILES+=("$f")
done

# Also check one level of subdirectories
for d in "$WORKDIR"/*/; do
    [ -d "$d" ] || continue
    for f in "$d"*.zip; do
        [ -e "$f" ] && INNER_ZIPS+=("$f")
    done
    for f in "$d"*.grl "$d"*.gr; do
        [ -e "$f" ] && PLAIN_FILES+=("$f")
    done
done

PASS=0
FAIL=0
TOTAL_TIME=0
declare -a RESULTS
INSTANCE_NUM=0

# Sort inner zips by name for predictable order
IFS=$'\n' INNER_ZIPS=($(sort <<<"${INNER_ZIPS[*]}")); unset IFS

# Process inner password-protected zips
for z in "${INNER_ZIPS[@]}"; do
    ((INSTANCE_NUM++))
    ZNAME="$(basename "$z")"
    echo "============================================"
    echo "  Instance $INSTANCE_NUM: $ZNAME"
    echo "============================================"
    read -rsp "  Password for $ZNAME: " ZIP_PASS
    echo ""

    INST_DIR=$(mktemp -d -p "$WORKDIR")

    UNZIP_START=$(date +%s%N)
    if ! unzip -q -o -P "$ZIP_PASS" "$z" -d "$INST_DIR" 2>/dev/null; then
        echo "  ERROR: Wrong password or corrupt zip"
        RESULTS+=("FAIL  0.000s  $ZNAME")
        ((FAIL++))
        echo ""
        continue
    fi
    UNZIP_END=$(date +%s%N)
    UNZIP_TIME=$(printf "%.3f" "$(echo "scale=6; ($UNZIP_END - $UNZIP_START) / 1000000000" | bc)")
    echo "  Unzipped in ${UNZIP_TIME}s"

    # Find graph files in the extracted directory
    GRAPH_FILES=()
    for f in "$INST_DIR"/*.grl "$INST_DIR"/*.gr; do
        [ -e "$f" ] && GRAPH_FILES+=("$f")
    done
    # Check subdirectories too
    for d in "$INST_DIR"/*/; do
        [ -d "$d" ] || continue
        for f in "$d"*.grl "$d"*.gr; do
            [ -e "$f" ] && GRAPH_FILES+=("$f")
        done
    done

    if [ ${#GRAPH_FILES[@]} -eq 0 ]; then
        echo "  No .grl/.gr files found in $ZNAME"
        RESULTS+=("FAIL  0.000s  $ZNAME")
        ((FAIL++))
        echo ""
        continue
    fi

    for f in "${GRAPH_FILES[@]}"; do
        NAME="$(basename "$f")"
        echo ""
        echo "  --- $NAME ---"

        START=$(date +%s%N)
        OUTPUT=$($PYTHON "$SOLVER" "$f" 2>&1) && STATUS="PASS" || STATUS="FAIL"
        END=$(date +%s%N)

        ELAPSED=$(printf "%.3f" "$(echo "scale=6; ($END - $START) / 1000000000" | bc)")
        TOTAL_TIME=$(printf "%.3f" "$(echo "$TOTAL_TIME + $ELAPSED" | bc)")

        echo "$OUTPUT" | sed 's/^/  /'
        echo ""
        echo "  Time: ${ELAPSED}s  [$STATUS]"

        RESULTS+=("$STATUS  ${ELAPSED}s  $ZNAME/$NAME")

        if [ "$STATUS" = "PASS" ]; then
            ((PASS++))
        else
            ((FAIL++))
        fi
    done
    echo ""
done

# Process any plain graph files (not inside inner zips)
for f in "${PLAIN_FILES[@]}"; do
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
