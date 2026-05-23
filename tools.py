"""
Agent 1 Tool Functions
- query_signal_history: simulates ClickHouse query for signal data along route
- predict_dead_zones:   estimates dead zones from signal history
- query_senso_knowledge: simulates Senso.ai knowledge base lookup

In production:
  query_signal_history → clickhouse_connect client.query(...)
  query_senso_knowledge → requests.post(SENSO_API_URL, ...)
"""

import json
from datetime import datetime, timedelta
from signal_data import (
    SIMULATED_SIGNAL_HISTORY,
    DEAD_ZONE_THRESHOLD_DBM,
    classify_severity,
)

# ---------------------------------------------------------------------------
# Route corridor registry — maps human route descriptions to segment keys
# ---------------------------------------------------------------------------
ROUTE_CORRIDORS = {
    "manhattan_to_newark": [
        "Manhattan_34th_10th",
        "Manhattan_34th_9th",
        "Tunnel_Approach_West",
        "Lincoln_Tunnel_Entry",
        "Lincoln_Tunnel_Mid",
        "Lincoln_Tunnel_Exit",
        "NJ_Turnpike_Exit_16E",
        "NJ_Turnpike_14C",
        "Newark_McCarter_Hwy",
        "Newark_Downtown",
    ],
    "default": [s["segment"] for s in SIMULATED_SIGNAL_HISTORY],
}

# Approximate distance between segments (miles) and average speed (mph)
SEGMENT_DISTANCE_MILES = 0.6
AVERAGE_SPEED_MPH = 18  # city + tunnel crawl


def _parse_departure(departure_time_str: str) -> datetime:
    """Parse flexible time strings. Falls back to 5 PM today."""
    today = datetime.now().date()
    formats = ["%H:%M", "%I:%M %p", "%I%p", "%Y-%m-%dT%H:%M"]
    for fmt in formats:
        try:
            t = datetime.strptime(departure_time_str, fmt)
            return datetime.combine(today, t.time())
        except ValueError:
            continue
    # Fallback
    return datetime.combine(today, datetime.strptime("17:00", "%H:%M").time())


# ---------------------------------------------------------------------------
# Tool 1 — query_signal_history
# ---------------------------------------------------------------------------
def query_signal_history(route: str, departure_time: str) -> dict:
    """
    Simulates a ClickHouse query:
      SELECT segment, lat, lon, avg_signal_dbm, sample_count
      FROM signal_quality
      WHERE corridor = {route}
        AND hour_of_day = {departure_hour}
      ORDER BY segment_order

    Returns list of segment readings with timing offsets from departure.
    """
    try:
        corridor_key = route.lower().replace(" ", "_").replace("-", "_")
        segments_in_order = ROUTE_CORRIDORS.get(
            corridor_key, ROUTE_CORRIDORS["default"]
        )

        departure_dt = _parse_departure(departure_time)
        departure_hour = departure_dt.hour

        results = []
        minutes_elapsed = 0.0
        segment_map = {s["segment"]: s for s in SIMULATED_SIGNAL_HISTORY}

        for seg_name in segments_in_order:
            seg = segment_map.get(seg_name)
            if not seg:
                continue

            # Scale signal slightly by time of day (rush hour degrades signal)
            rush_penalty = -4 if 16 <= departure_hour <= 19 else 0
            adjusted_signal = seg["avg_signal_dbm"] + rush_penalty

            eta_at_segment = departure_dt + timedelta(minutes=minutes_elapsed)

            results.append(
                {
                    "segment": seg["segment"],
                    "lat": seg["lat"],
                    "lon": seg["lon"],
                    "avg_signal_dbm": round(adjusted_signal, 1),
                    "sample_count": seg["sample_count"],
                    "eta_at_segment": eta_at_segment.strftime("%H:%M"),
                }
            )
            minutes_elapsed += (SEGMENT_DISTANCE_MILES / AVERAGE_SPEED_MPH) * 60

        return {
            "status": "success",
            "source": "clickhouse_simulated",
            "route": route,
            "departure_time": departure_time,
            "segments": results,
            "note": "Simulated data — production queries real ClickHouse Cloud table",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Tool 2 — predict_dead_zones
# ---------------------------------------------------------------------------
def predict_dead_zones(signal_history: list) -> dict:
    """
    Takes the output of query_signal_history['segments'] and identifies
    contiguous dead zones (signal below threshold), merging adjacent weak
    segments into a single dead zone entry.

    Returns structured dead zone list ready for Agent 2 handoff.
    """
    try:
        dead_zone_segments = [
            s for s in signal_history if s["avg_signal_dbm"] <= DEAD_ZONE_THRESHOLD_DBM
        ]

        if not dead_zone_segments:
            return {
                "status": "success",
                "dead_zones": [],
                "message": "No dead zones detected on this route.",
            }

        # Merge contiguous segments into dead zone windows
        dead_zones = []
        current_group = [dead_zone_segments[0]]

        for seg in dead_zone_segments[1:]:
            current_group.append(seg)

        # For demo simplicity: treat each contiguous group as one dead zone
        # Production: cluster by time proximity
        groups = []
        group = [dead_zone_segments[0]]
        for seg in dead_zone_segments[1:]:
            # If ETA gap is small, merge
            prev_eta = datetime.strptime(group[-1]["eta_at_segment"], "%H:%M")
            this_eta = datetime.strptime(seg["eta_at_segment"], "%H:%M")
            gap_minutes = (this_eta - prev_eta).seconds / 60
            if gap_minutes <= 5:
                group.append(seg)
            else:
                groups.append(group)
                group = [seg]
        groups.append(group)

        for group in groups:
            worst = min(group, key=lambda s: s["avg_signal_dbm"])
            first = group[0]
            last = group[-1]

            first_eta = datetime.strptime(first["eta_at_segment"], "%H:%M")
            last_eta = datetime.strptime(last["eta_at_segment"], "%H:%M")
            duration = max(
                round((last_eta - first_eta).seconds / 60 + 1), 1
            )  # at least 1 min

            dead_zones.append(
                {
                    "location": {
                        "human_readable": worst["segment"].replace("_", " "),
                        "lat": worst["lat"],
                        "lon": worst["lon"],
                    },
                    "start_time": first["eta_at_segment"],
                    "duration_minutes": duration,
                    "severity": classify_severity(worst["avg_signal_dbm"]),
                    "avg_signal_dbm": worst["avg_signal_dbm"],
                    "segments_affected": [s["segment"] for s in group],
                }
            )

        return {
            "status": "success",
            "dead_zone_count": len(dead_zones),
            "dead_zones": dead_zones,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Tool 3 — query_senso_knowledge
# ---------------------------------------------------------------------------
SENSO_KNOWLEDGE_BASE = {
    "lincoln_tunnel": {
        "known_dead_zone": True,
        "reason": "Underground tunnel with no cell tower penetration",
        "typical_duration_minutes": 3,
        "severity": "high",
        "coordinates": {"lat": 40.7621, "lon": -74.0312},
    },
    "newark_mccarter": {
        "known_dead_zone": True,
        "reason": "Urban canyon, overlapping tower handoff failure zone",
        "typical_duration_minutes": 2,
        "severity": "medium",
        "coordinates": {"lat": 40.7357, "lon": -74.1724},
    },
    "nj_turnpike_14c": {
        "known_dead_zone": False,
        "reason": "Generally good coverage, occasional congestion degradation",
        "typical_duration_minutes": 0,
        "severity": "low",
        "coordinates": {"lat": 40.7282, "lon": -74.1601},
    },
}


def query_senso_knowledge(route: str) -> dict:
    """
    Simulates Senso.ai knowledge base query for known dead zones on a route.
    Production: POST to Senso API with route context, get structured knowledge back.
    """
    try:
        route_lower = route.lower()
        results = []

        for key, entry in SENSO_KNOWLEDGE_BASE.items():
            if any(word in route_lower for word in key.split("_")):
                results.append({"corridor": key, **entry})

        # Always include Lincoln Tunnel for Manhattan→Newark routes
        if "newark" in route_lower or "manhattan" in route_lower:
            lt = SENSO_KNOWLEDGE_BASE["lincoln_tunnel"]
            if not any(r["corridor"] == "lincoln_tunnel" for r in results):
                results.append({"corridor": "lincoln_tunnel", **lt})

        return {
            "status": "success",
            "source": "senso_ai_simulated",
            "known_dead_zones": results,
            "note": "Simulated Senso.ai knowledge base — production queries live Senso API",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Tool registry — maps tool names to callables for the agent loop
# ---------------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "query_signal_history": query_signal_history,
    "predict_dead_zones": predict_dead_zones,
    "query_senso_knowledge": query_senso_knowledge,
}

# ---------------------------------------------------------------------------
# OpenAI-compatible tool schemas
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_senso_knowledge",
            "description": (
                "Query the Senso.ai knowledge base for known dead zones along a route. "
                "Always call this FIRST before querying signal history — it returns "
                "pre-verified corridor knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "route": {
                        "type": "string",
                        "description": "Human-readable route description, e.g. 'Manhattan to Newark'",
                    }
                },
                "required": ["route"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_signal_history",
            "description": (
                "Query historical cellular signal quality data from ClickHouse for each "
                "segment along the route. Returns signal strength (dBm) per segment with "
                "estimated arrival times based on departure time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "route": {
                        "type": "string",
                        "description": "Route identifier, e.g. 'manhattan_to_newark'",
                    },
                    "departure_time": {
                        "type": "string",
                        "description": "Departure time as HH:MM (24h) or '5:00 PM'",
                    },
                },
                "required": ["route", "departure_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_dead_zones",
            "description": (
                "Analyze signal history segments to identify and classify dead zones. "
                "Pass the 'segments' list from query_signal_history output. "
                "Returns structured dead zone list with location, start_time, "
                "duration_minutes, and severity for each zone."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "signal_history": {
                        "type": "array",
                        "description": "List of segment objects from query_signal_history",
                        "items": {"type": "object"},
                    }
                },
                "required": ["signal_history"],
            },
        },
    },
]
