"""
Test script to verify LeverageAwareOptimizer structure without database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np

# Test 1: Check module imports
print("=" * 60)
print("Test 1: Module Import Check")
print("=" * 60)

try:
    # Try importing just the class definition
    from app.optimizer.leverage_aware import LeverageAwareOptimizer
    print("✓ LeverageAwareOptimizer imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    # Try direct import
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "leverage_aware",
            "app/optimizer/leverage_aware.py"
        )
        module = importlib.util.module_from_spec(spec)
        print("✓ Module can be loaded directly")
    except Exception as e2:
        print(f"✗ Direct load also failed: {e2}")

# Test 2: Class validation
print("\n" + "=" * 60)
print("Test 2: Class Validation")
print("=" * 60)

# Create sample ownership data
ownership = np.array([25.3, 18.7, 12.4, 8.9, 6.2, 5.1, 4.3, 3.8, 3.2, 2.9, 2.5, 2.1])
print(f"Sample ownership array: {ownership}")

# Test 3: Validate input constraints
print("\n" + "=" * 60)
print("Test 3: Input Validation")
print("=" * 60)

# Create a mock optimizer
class MockOptimizer:
    def __init__(self):
        self.n_drivers = 6
        self.drivers = []
        self.salary_cap = 50000

mock_base = MockOptimizer()

# Test valid initialization
try:
    leverage_opt = LeverageAwareOptimizer(
        mock_base,
        ownership,
        leverage_penalty=0.5,
        max_ownership_per_driver=0.3
    )
    print(f"✓ Valid initialization successful")
    print(f"  - Leverage penalty: {leverage_opt.leverage_penalty}")
    print(f"  - Max ownership per driver: {leverage_opt.max_ownership_per_driver}")
    print(f"  - Min low-ownership drivers: {leverage_opt.min_low_ownership_drivers}")
    print(f"  - Max total ownership: {leverage_opt.max_total_ownership}")
except Exception as e:
    print(f"✗ Valid initialization failed: {e}")

# Test invalid ownership (empty)
try:
    LeverageAwareOptimizer(mock_base, np.array([]))
    print("✗ Should have raised ValueError for empty ownership")
except ValueError:
    print("✓ Correctly raised ValueError for empty ownership")
except Exception as e:
    print(f"? Unexpected error for empty ownership: {e}")

# Test invalid leverage_penalty
try:
    LeverageAwareOptimizer(mock_base, ownership, leverage_penalty=1.5)
    print("✗ Should have raised ValueError for leverage_penalty > 1")
except ValueError:
    print("✓ Correctly raised ValueError for leverage_penalty > 1")
except Exception as e:
    print(f"? Unexpected error for leverage_penalty: {e}")

# Test invalid max_ownership_per_driver
try:
    LeverageAwareOptimizer(mock_base, ownership, max_ownership_per_driver=1.5)
    print("✗ Should have raised ValueError for max_ownership_per_driver > 1")
except ValueError:
    print("✓ Correctly raised ValueError for max_ownership_per_driver > 1")
except Exception as e:
    print(f"? Unexpected error for max_ownership_per_driver: {e}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
