"""
Smoke test — verifies tool functions work correctly without needing an API key.
Run: python test_tools.py
"""

import json
from tools import query_senso_knowledge, query_signal_history, predict_dead_zones

ROUTE = "Manhattan to Newark"
DEPARTURE = "17:00"

print("=" * 60)
print("SMOKE TEST — Agent 1 Tool Functions")
print("=" * 60)

# ── Test 1: Senso knowledge base ──────────────────────────────
print("\n[1] query_senso_knowledge")
senso = query_senso_knowledge(ROUTE)
print(json.dumps(senso, indent=2))
assert senso["status"] == "success"
assert len(senso["known_dead_zones"]) > 0
print("✓ PASS")

# ── Test 2: Signal history ────────────────────────────────────
print("\n[2] query_signal_history")
history = query_signal_history(ROUTE, DEPARTURE)
print(json.dumps(history, indent=2))
assert history["status"] == "success"
assert len(history["segments"]) > 0
print("✓ PASS")

# ── Test 3: Dead zone prediction ─────────────────────────────
print("\n[3] predict_dead_zones")
dz = predict_dead_zones(history["segments"])
print(json.dumps(dz, indent=2))
assert dz["status"] == "success"
assert "dead_zones" in dz

# Validate output contract
for zone in dz["dead_zones"]:
    assert "location" in zone, f"Missing location: {zone}"
    assert "lat" in zone["location"] and "lon" in zone["location"]
    assert "start_time" in zone
    assert "duration_minutes" in zone
    assert "severity" in zone
    assert zone["severity"] in ("low", "medium", "high")

print(f"✓ PASS — {dz['dead_zone_count']} dead zone(s) found")

print("\n" + "=" * 60)
print("ALL TESTS PASSED — tools.py is working correctly")
print("Agent 2 output contract: ✓ location ✓ start_time ✓ duration_minutes ✓ severity")
print("=" * 60)
