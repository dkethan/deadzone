"""
Quick test — verifies query_signal_strength works with one coordinate.
Run: python backend/tools/test_signal.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.tools.signal import query_signal_strength

TEST_WAYPOINTS = [
    {"lat": 40.7128, "lng": -74.0060},  # Lower Manhattan
]

print("Testing query_signal_strength with 1 coordinate...")
result = query_signal_strength(TEST_WAYPOINTS, provider="TMO")
print(json.dumps(result, indent=2))

assert "waypoints_checked" in result
assert "dead_zones_found" in result
assert "signal_data" in result
assert "dead_zone_segments" in result
assert result["waypoints_checked"] == 1

print("\n✓ PASS — function returned correct structure")
print(f"  Signal at test point: {result['signal_data'][0].get('signal_dbm')} dBm")
print(f"  Dead zone: {result['signal_data'][0].get('is_dead_zone')}")
