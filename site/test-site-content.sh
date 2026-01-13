#!/bin/bash
# Test script for marketing site content verification
# Run: ./site/test-site-content.sh

SITE_FILE="site/index.html"
FAILED=0

echo "Testing marketing site content..."
echo ""

# Test 1: Redis/ElastiCache mentioned anywhere in the Mermaid diagram section
# The diagram section is between "Infrastructure Overview" and the closing mermaid div
echo -n "Test 1: Redis in Infrastructure Mermaid diagram... "
if grep -A 50 "Infrastructure Overview" "$SITE_FILE" | grep -q "ElastiCache"; then
    echo "PASS"
else
    echo "FAIL - ElastiCache not found in Infrastructure Overview diagram"
    FAILED=1
fi

# Test 2: ElastiCache in tech stack Infrastructure card
# Look for ElastiCache in the Infrastructure section of tech-grid
echo -n "Test 2: ElastiCache in Infrastructure tech card... "
if grep -A 10 "<h4>Infrastructure</h4>" "$SITE_FILE" | grep -q "ElastiCache"; then
    echo "PASS"
else
    echo "FAIL - ElastiCache not found in Infrastructure tech stack"
    FAILED=1
fi

# Test 3: Lambda connects to Redis/ElastiCache in diagram
echo -n "Test 3: Lambda-Redis connection in diagram... "
if grep -q "Lambda.*Cache\|Lambda.*Redis" "$SITE_FILE"; then
    echo "PASS"
else
    echo "FAIL - Lambda-Redis/Cache connection not found in diagram"
    FAILED=1
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo "All tests PASSED"
    exit 0
else
    echo "Some tests FAILED"
    exit 1
fi
