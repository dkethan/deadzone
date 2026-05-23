import os
import requests
import polyline
from dotenv import load_dotenv

load_dotenv()

def get_route_waypoints(origin: str, destination: str, num_points: int = 20) -> dict:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    r = requests.get("https://maps.googleapis.com/maps/api/directions/json", params={
        "origin": origin,
        "destination": destination,
        "key": key
    })
    data = r.json()
    if data["status"] != "OK":
        return {"error": data["status"]}

    encoded = data["routes"][0]["overview_polyline"]["points"]
    coords = polyline.decode(encoded)

    step = max(1, len(coords) // num_points)
    sampled = coords[::step][:num_points]

    return {
        "origin": origin,
        "destination": destination,
        "waypoints": [{"lat": lat, "lng": lng} for lat, lng in sampled],
        "total_points": len(sampled)
    }

