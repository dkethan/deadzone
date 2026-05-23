"""
Simulated ClickHouse signal quality data.
In production: clickhouse-connect queries a real CH Cloud table.
Schema: route_segment, lat, lon, avg_signal_dbm, sample_count, recorded_at
"""

SIMULATED_SIGNAL_HISTORY = [
    # Manhattan surface streets — decent signal
    {"segment": "Manhattan_34th_10th", "lat": 40.7506, "lon": -74.0002, "avg_signal_dbm": -72, "sample_count": 412, "hour_of_day": 17},
    {"segment": "Manhattan_34th_9th",  "lat": 40.7506, "lon": -73.9983, "avg_signal_dbm": -69, "sample_count": 389, "hour_of_day": 17},

    # Lincoln Tunnel approach — signal degrades
    {"segment": "Tunnel_Approach_West", "lat": 40.7590, "lon": -74.0028, "avg_signal_dbm": -88, "sample_count": 201, "hour_of_day": 17},
    {"segment": "Lincoln_Tunnel_Entry", "lat": 40.7613, "lon": -74.0213, "avg_signal_dbm": -104, "sample_count": 198, "hour_of_day": 17},

    # Lincoln Tunnel proper — dead zone
    {"segment": "Lincoln_Tunnel_Mid",  "lat": 40.7621, "lon": -74.0312, "avg_signal_dbm": -115, "sample_count": 187, "hour_of_day": 17},
    {"segment": "Lincoln_Tunnel_Exit", "lat": 40.7629, "lon": -74.0401, "avg_signal_dbm": -112, "sample_count": 192, "hour_of_day": 17},

    # NJ Turnpike — variable
    {"segment": "NJ_Turnpike_Exit_16E","lat": 40.7489, "lon": -74.0891, "avg_signal_dbm": -78, "sample_count": 320, "hour_of_day": 17},
    {"segment": "NJ_Turnpike_14C",     "lat": 40.7282, "lon": -74.1601, "avg_signal_dbm": -75, "sample_count": 298, "hour_of_day": 17},

    # Newark — urban canyon partial dead zones
    {"segment": "Newark_McCarter_Hwy", "lat": 40.7357, "lon": -74.1724, "avg_signal_dbm": -91, "sample_count": 156, "hour_of_day": 17},
    {"segment": "Newark_Downtown",     "lat": 40.7357, "lon": -74.1724, "avg_signal_dbm": -85, "sample_count": 201, "hour_of_day": 17},
]

# Dead zone threshold: signal below this is considered a dead zone
DEAD_ZONE_THRESHOLD_DBM = -95

# Severity bands
def classify_severity(avg_signal_dbm: float) -> str:
    if avg_signal_dbm <= -110:
        return "high"
    elif avg_signal_dbm <= -100:
        return "medium"
    else:
        return "low"
