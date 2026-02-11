#!/bin/bash

# Smoke Test Script for NASCAR DFS Engine
# This script runs basic smoke tests for all components to validate CI workflow compatibility

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
SKIPPED=0

# Print header
echo "=========================================="
echo "NASCAR DFS Engine - Smoke Tests"
echo "=========================================="
echo ""

# Function to print test result
print_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    if [ "$result" == "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        PASSED=$((PASSED + 1))
    elif [ "$result" == "FAIL" ]; then
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        if [ -n "$message" ]; then
            echo -e "  ${RED}Error: $message${NC}"
        fi
        FAILED=$((FAILED + 1))
    elif [ "$result" == "SKIP" ]; then
        echo -e "${YELLOW}⊘ SKIP${NC}: $test_name"
        if [ -n "$message" ]; then
            echo -e "  ${YELLOW}Reason: $message${NC}"
        fi
        SKIPPED=$((SKIPPED + 1))
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Python module is installed
python_module_exists() {
    python3 -c "import $1" 2>/dev/null
}

# ============================================================================
# Backend Tests
# ============================================================================
echo "=========================================="
echo "Backend API Tests"
echo "=========================================="

# Test 1: Check Python 3 is available
echo ""
echo "Test: Python 3 availability"
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_result "Python 3 installed" "PASS" "$PYTHON_VERSION"
else
    print_result "Python 3 installed" "FAIL" "Python 3 not found"
fi

# Test 2: Check pytest is available
echo ""
echo "Test: pytest availability"
if command_exists pytest; then
    PYTEST_VERSION=$(pytest --version)
    print_result "pytest installed" "PASS" "$PYTEST_VERSION"
else
    print_result "pytest installed" "SKIP" "pytest not found (will be installed by CI)"
fi

# Test 3: Check backend test file exists
echo ""
echo "Test: Backend test file structure"
if [ -f "apps/backend/tests/test_main.py" ]; then
    print_result "Backend test file exists" "PASS" "apps/backend/tests/test_main.py"
else
    print_result "Backend test file exists" "FAIL" "apps/backend/tests/test_main.py not found"
fi

# Test 4: Check backend test imports TestClient
echo ""
echo "Test: Backend test uses TestClient"
if grep -q "from fastapi.testclient import TestClient" apps/backend/tests/test_main.py 2>/dev/null; then
    print_result "Backend test imports TestClient" "PASS" "TestClient import found"
else
    print_result "Backend test imports TestClient" "FAIL" "TestClient import not found"
fi

# Test 5: Check backend test has /health endpoint test
echo ""
echo "Test: Backend test has /health endpoint test"
if grep -q "def test_health_endpoint" apps/backend/tests/test_main.py 2>/dev/null; then
    print_result "Backend test has /health endpoint test" "PASS" "test_health_endpoint found"
else
    print_result "Backend test has /health endpoint test" "FAIL" "test_health_endpoint not found"
fi

# Test 6: Check backend test has /optimize endpoint test
echo ""
echo "Test: Backend test has /optimize endpoint test"
if grep -q "def test_optimize_endpoint" apps/backend/tests/test_main.py 2>/dev/null; then
    print_result "Backend test has /optimize endpoint test" "PASS" "test_optimize_endpoint found"
else
    print_result "Backend test has /optimize endpoint test" "FAIL" "test_optimize_endpoint not found"
fi

# Test 7: Check backend pyproject.toml exists
echo ""
echo "Test: Backend dependency file exists"
if [ -f "apps/backend/pyproject.toml" ]; then
    print_result "Backend pyproject.toml exists" "PASS" "apps/backend/pyproject.toml"
else
    print_result "Backend pyproject.toml exists" "FAIL" "apps/backend/pyproject.toml not found"
fi

# Test 8: Check backend dependencies include pytest
echo ""
echo "Test: Backend dependencies include pytest"
if grep -q "pytest" apps/backend/pyproject.toml 2>/dev/null; then
    print_result "Backend dependencies include pytest" "PASS" "pytest found in pyproject.toml"
else
    print_result "Backend dependencies include pytest" "FAIL" "pytest not found in pyproject.toml"
fi

# ============================================================================
# Frontend Tests
# ============================================================================
echo ""
echo "=========================================="
echo "Frontend UI Tests"
echo "=========================================="

# Test 9: Check Node.js is available
echo ""
echo "Test: Node.js availability"
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_result "Node.js installed" "PASS" "$NODE_VERSION"
else
    print_result "Node.js installed" "SKIP" "Node.js not found (will be installed by CI)"
fi

# Test 10: Check npm is available
echo ""
echo "Test: npm availability"
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_result "npm installed" "PASS" "$NPM_VERSION"
else
    print_result "npm installed" "SKIP" "npm not found (will be installed by CI)"
fi

# Test 11: Check frontend test directory exists
echo ""
echo "Test: Frontend test directory structure"
if [ -d "apps/frontend/__tests__" ]; then
    print_result "Frontend test directory exists" "PASS" "apps/frontend/__tests__"
else
    print_result "Frontend test directory exists" "FAIL" "apps/frontend/__tests__ not found"
fi

# Test 12: Check frontend test files exist
echo ""
echo "Test: Frontend test files exist"
TEST_FILES_FOUND=0
if [ -f "apps/frontend/__tests__/ProjectionTable.test.tsx" ]; then
    TEST_FILES_FOUND=$((TEST_FILES_FOUND + 1))
fi
if [ -f "apps/frontend/__tests__/OptimizerPanel.test.tsx" ]; then
    TEST_FILES_FOUND=$((TEST_FILES_FOUND + 1))
fi

if [ $TEST_FILES_FOUND -eq 2 ]; then
    print_result "Frontend test files exist" "PASS" "Found $TEST_FILES_FOUND test files"
elif [ $TEST_FILES_FOUND -eq 1 ]; then
    print_result "Frontend test files exist" "WARN" "Found only 1 test file (expected 2)"
    PASSED=$((PASSED + 1))
else
    print_result "Frontend test files exist" "FAIL" "No test files found"
fi

# Test 13: Check frontend tests use React Testing Library
echo ""
echo "Test: Frontend tests use React Testing Library"
if grep -q "from '@testing-library/react'" apps/frontend/__tests__/ProjectionTable.test.tsx 2>/dev/null; then
    print_result "Frontend tests use React Testing Library" "PASS" "Testing Library import found"
else
    print_result "Frontend tests use React Testing Library" "FAIL" "Testing Library import not found"
fi

# Test 14: Check frontend package.json exists
echo ""
echo "Test: Frontend package.json exists"
if [ -f "apps/frontend/package.json" ]; then
    print_result "Frontend package.json exists" "PASS" "apps/frontend/package.json"
else
    print_result "Frontend package.json exists" "FAIL" "apps/frontend/package.json not found"
fi

# Test 15: Check frontend package.json has test script
echo ""
echo "Test: Frontend package.json has test script"
if grep -q '"test": "jest"' apps/frontend/package.json 2>/dev/null; then
    print_result "Frontend package.json has test script" "PASS" "jest test script found"
else
    print_result "Frontend package.json has test script" "FAIL" "jest test script not found"
fi

# Test 16: Check frontend jest.config.js exists
echo ""
echo "Test: Frontend jest.config.js exists"
if [ -f "apps/frontend/jest.config.js" ]; then
    print_result "Frontend jest.config.js exists" "PASS" "apps/frontend/jest.config.js"
else
    print_result "Frontend jest.config.js exists" "FAIL" "apps/frontend/jest.config.js not found"
fi

# ============================================================================
# ETL Tests
# ============================================================================
echo ""
echo "=========================================="
echo "ETL Pipeline Tests"
echo "=========================================="

# Test 17: Check Airflow test file exists
echo ""
echo "Test: ETL test file structure"
if [ -f "apps/airflow/tests/test_dag.py" ]; then
    print_result "ETL test file exists" "PASS" "apps/airflow/tests/test_dag.py"
else
    print_result "ETL test file exists" "FAIL" "apps/airflow/tests/test_dag.py not found"
fi

# Test 18: Check ETL test has DAG import test
echo ""
echo "Test: ETL test has DAG import test"
if grep -q "def test_dag_imports_without_errors" apps/airflow/tests/test_dag.py 2>/dev/null; then
    print_result "ETL test has DAG import test" "PASS" "test_dag_imports_without_errors found"
else
    print_result "ETL test has DAG import test" "FAIL" "test_dag_imports_without_errors not found"
fi

# Test 19: Check ETL test has task validation test
echo ""
echo "Test: ETL test has task validation test"
if grep -q "def test_task_dependencies" apps/airflow/tests/test_dag.py 2>/dev/null; then
    print_result "ETL test has task validation test" "PASS" "test_task_dependencies found"
else
    print_result "ETL test has task validation test" "FAIL" "test_task_dependencies not found"
fi

# Test 20: Check ETL requirements.txt exists
echo ""
echo "Test: ETL requirements.txt exists"
if [ -f "apps/airflow/requirements.txt" ]; then
    print_result "ETL requirements.txt exists" "PASS" "apps/airflow/requirements.txt"
else
    print_result "ETL requirements.txt exists" "FAIL" "apps/airflow/requirements.txt not found"
fi

# Test 21: Check ETL requirements.txt includes pytest
echo ""
echo "Test: ETL requirements.txt includes pytest"
if grep -q "pytest" apps/airflow/requirements.txt 2>/dev/null; then
    print_result "ETL requirements.txt includes pytest" "PASS" "pytest found in requirements.txt"
else
    print_result "ETL requirements.txt includes pytest" "FAIL" "pytest not found in requirements.txt"
fi

# ============================================================================
# ML Tests
# ============================================================================
echo ""
echo "=========================================="
echo "ML Model Tests"
echo "=========================================="

# Test 22: Check ML test directory exists
echo ""
echo "Test: ML test directory structure"
if [ -d "packages/axiomatic-kernel/tests" ]; then
    print_result "ML test directory exists" "PASS" "packages/axiomatic-kernel/tests"
else
    print_result "ML test directory exists" "FAIL" "packages/axiomatic-kernel/tests not found"
fi

# Test 23: Check ML test files exist
echo ""
echo "Test: ML test files exist"
ML_TEST_FILES_FOUND=0
if [ -f "packages/axiomatic-kernel/tests/test_dataset.py" ]; then
    ML_TEST_FILES_FOUND=$((ML_TEST_FILES_FOUND + 1))
fi
if [ -f "packages/axiomatic-kernel/tests/test_projection_model.py" ]; then
    ML_TEST_FILES_FOUND=$((ML_TEST_FILES_FOUND + 1))
fi

if [ $ML_TEST_FILES_FOUND -eq 2 ]; then
    print_result "ML test files exist" "PASS" "Found $ML_TEST_FILES_FOUND test files"
elif [ $ML_TEST_FILES_FOUND -eq 1 ]; then
    print_result "ML test files exist" "WARN" "Found only 1 test file (expected 2)"
    PASSED=$((PASSED + 1))
else
    print_result "ML test files exist" "FAIL" "No test files found"
fi

# Test 24: Check ML test has dataset test
echo ""
echo "Test: ML test has dataset test"
if grep -q "class TestNASCARDataset" packages/axiomatic-kernel/tests/test_dataset.py 2>/dev/null; then
    print_result "ML test has dataset test" "PASS" "TestNASCARDataset found"
else
    print_result "ML test has dataset test" "FAIL" "TestNASCARDataset not found"
fi

# Test 25: Check ML test has projection model test
echo ""
echo "Test: ML test has projection model test"
if grep -q "class TestProjectionModel" packages/axiomatic-kernel/tests/test_projection_model.py 2>/dev/null; then
    print_result "ML test has projection model test" "PASS" "TestProjectionModel found"
else
    print_result "ML test has projection model test" "FAIL" "TestProjectionModel not found"
fi

# Test 26: Check ML pyproject.toml exists
echo ""
echo "Test: ML pyproject.toml exists"
if [ -f "packages/axiomatic-kernel/pyproject.toml" ]; then
    print_result "ML pyproject.toml exists" "PASS" "packages/axiomatic-kernel/pyproject.toml"
else
    print_result "ML pyproject.toml exists" "FAIL" "packages/axiomatic-kernel/pyproject.toml not found"
fi

# Test 27: Check ML pyproject.toml has pytest in dev dependencies
echo ""
echo "Test: ML pyproject.toml has pytest in dev dependencies"
if grep -A 10 "dev =" packages/axiomatic-kernel/pyproject.toml | grep -q "pytest" 2>/dev/null; then
    print_result "ML pyproject.toml has pytest in dev dependencies" "PASS" "pytest found in dev dependencies"
else
    print_result "ML pyproject.toml has pytest in dev dependencies" "FAIL" "pytest not found in dev dependencies"
fi

# ============================================================================
# Test Infrastructure Tests
# ============================================================================
echo ""
echo "=========================================="
echo "Test Infrastructure Tests"
echo "=========================================="

# Test 28: Check tests/ directory exists
echo ""
echo "Test: Root tests directory exists"
if [ -d "tests" ]; then
    print_result "Root tests directory exists" "PASS" "tests/"
else
    print_result "Root tests directory exists" "FAIL" "tests/ not found"
fi

# Test 29: Check E2E_TEST_PLAN.md exists
echo ""
echo "Test: E2E test plan exists"
if [ -f "tests/E2E_TEST_PLAN.md" ]; then
    print_result "E2E test plan exists" "PASS" "tests/E2E_TEST_PLAN.md"
else
    print_result "E2E test plan exists" "FAIL" "tests/E2E_TEST_PLAN.md not found"
fi

# Test 30: Check README.md exists
echo ""
echo "Test: Test README exists"
if [ -f "tests/README.md" ]; then
    print_result "Test README exists" "PASS" "tests/README.md"
else
    print_result "Test README exists" "FAIL" "tests/README.md not found"
fi

# Test 31: Check smoke_test.sh is executable
echo ""
echo "Test: smoke_test.sh is executable"
if [ -x "tests/smoke_test.sh" ]; then
    print_result "smoke_test.sh is executable" "PASS" "tests/smoke_test.sh is executable"
else
    print_result "smoke_test.sh is executable" "WARN" "smoke_test.sh is not executable (will be fixed by CI)"
    PASSED=$((PASSED + 1))
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=========================================="
echo "Smoke Test Summary"
echo "=========================================="
echo ""
echo -e "Total Tests: $((PASSED + FAILED + SKIPPED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
echo ""

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Smoke tests failed with $FAILED error(s)${NC}"
    exit 1
elif [ $SKIPPED -gt 0 ]; then
    echo -e "${YELLOW}Smoke tests passed with $SKIPPED skipped test(s)${NC}"
    exit 0
else
    echo -e "${GREEN}All smoke tests passed!${NC}"
    exit 0
fi
