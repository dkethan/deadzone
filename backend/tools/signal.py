"""
signal.py — CoverageMap API integration for Agent 1
Tool function: query_signal_strength(waypoints, provider='TMO')

Called by Shageenth's agent loop as a tool. No agent logic here.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

COVERAGEMAP_API_KEY = os.getenv("COVERAGEMAP_API_KEY")
COVERAGEMAP_URL = "https://enterprise.coveragemap.com/api/v1/signal-strength/lookup"

DEAD_ZONE_THRESHOLD_DBM = -105  # below this = dead zone


def query_signal_strength(waypoints: list, provider: str = "TMO") -> dict:
    """
    Query CoverageMap API for signal strength at each waypoint.

    Args:
        waypoints: list of {"lat": float, "lng": float} dicts
        provider:  carrier code — "TMO" for T-Mobile (default)

    Returns:
        {
            "waypoints_checked": int,
            "dead_zones_found": int,
            "signal_data": [...],        # all points with signal info
            "dead_zone_segments": [...], # only the dead zone points
        }
    """
    if not COVERAGEMAP_API_KEY:
        raise EnvironmentError(
            "COVERAGEMAP_API_KEY not set. Add it to your .env file."
        )

    headers = {"Authorization": f"Bearer {COVERAGEMAP_API_KEY}"}

    signal_data = []
    dead_zone_segments = []

    for wp in waypoints:
        params = {
            "latitude": wp["lat"],
            "longitude": wp["lng"],
            "providers": provider,
        }

        try:
            response = requests.get(
                COVERAGEMAP_URL,
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # API returns a list — grab first result for our provider
            result = data[0] if data else {}
            signal_dbm = result.get("signal", {}).get("signal", None)
            is_dead_zone = (
                signal_dbm is not None and signal_dbm < DEAD_ZONE_THRESHOLD_DBM
            )

            point = {
                "lat": wp["lat"],
                "lng": wp["lng"],
                "provider": provider,
                "signal_dbm": signal_dbm,
                "is_dead_zone": is_dead_zone,
                "raw": result,
            }

        except requests.exceptions.RequestException as e:
            point = {
                "lat": wp["lat"],
                "lng": wp["lng"],
                "provider": provider,
                "signal_dbm": None,
                "is_dead_zone": False,
                "error": str(e),
            }

        signal_data.append(point)
        if point["is_dead_zone"]:
            dead_zone_segments.append(point)

    return {
        "waypoints_checked": len(waypoints),
        "dead_zones_found": len(dead_zone_segments),
        "signal_data": signal_data,
        "dead_zone_segments": dead_zone_segments,
    }
