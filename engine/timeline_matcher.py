"""Timeline, Location, and Direction Continuity Matching Engine.
Evaluates Who + Where + When + Direction across reports and sightings.
"""
import math
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

# Landmark coordinates for realistic disaster simulation (e.g. Wayland Valley Flood Zone)
LANDMARK_COORDINATES = {
    "Sector 1 River Basin": (12.9716, 77.5946),
    "Bridge East Crossway": (12.9760, 77.6010),
    "Relief Camp Alpha": (12.9820, 77.6100),
    "Central General Hospital": (12.9650, 77.5850),
    "Highway Shelter 4": (12.9900, 77.6250),
    "Community Stadium": (12.9550, 77.6050),
    "North Hill Checkpoint": (12.9950, 77.5900),
    "Old Temple Refuge": (12.9600, 77.6200),
    "Railway Station Shelter": (12.9780, 77.5700),
    "West Ridge Evacuation Zone": (12.9500, 77.5600)
}

# Direction vector mapping (in degrees from North: 0 = North, 90 = East, 180 = South, 270 = West)
DIRECTION_ANGLES = {
    "North": 0,
    "Northeast": 45,
    "East": 90,
    "Southeast": 135,
    "South": 180,
    "Southwest": 225,
    "West": 270,
    "Northwest": 315,
    "Towards Relief Camp Alpha": 55,
    "Towards Central Hospital": 210,
    "Towards River Crossing Bridge": 80,
    "Towards Highway Shelter 4": 50,
    "Towards Community Stadium": 150,
    "Stationary / Unmoved": None
}


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance in kilometers between two GPS coordinates using Haversine formula."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_coordinates(place_name: str, fallback_lat: float = None, fallback_lon: float = None) -> Tuple[float, float]:
    """Retrieve GPS coordinates for a place name or use fallback."""
    if fallback_lat is not None and fallback_lon is not None:
        return (float(fallback_lat), float(fallback_lon))
    
    if place_name in LANDMARK_COORDINATES:
        return LANDMARK_COORDINATES[place_name]
    
    # Fuzzy match with landmarks
    for name, coords in LANDMARK_COORDINATES.items():
        if name.lower() in place_name.lower() or place_name.lower() in name.lower():
            return coords
            
    # Default disaster zone center
    return (12.9716, 77.5946)


def parse_timestamp(ts: Any) -> datetime:
    """Parse various timestamp formats safely into a UTC datetime."""
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if not ts:
        return datetime.now(timezone.utc)
    
    s = str(ts).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        # Fallback to current time
        return datetime.now(timezone.utc)


def calculate_direction_alignment(dir1: str, dir2: str) -> float:
    """Calculate directional consistency between two reports on a scale 0.0 to 1.0.
    1.0 = exact same direction, 0.0 = opposite direction.
    """
    if not dir1 or not dir2:
        return 0.5  # Neutral when unspecified
    
    # Direct string match
    if dir1.lower() == dir2.lower():
        return 1.0
        
    ang1 = DIRECTION_ANGLES.get(dir1)
    ang2 = DIRECTION_ANGLES.get(dir2)
    
    if ang1 is None or ang2 is None:
        return 0.6  # Neutral/supportive
        
    diff = abs(ang1 - ang2) % 360
    if diff > 180:
        diff = 360 - diff
        
    # Scale: 0 deg diff -> 1.0; 45 deg -> 0.85; 90 deg -> 0.5; 180 deg -> 0.0
    return max(0.0, 1.0 - (diff / 180.0))


def analyze_timeline_continuity(
    sighting_a: Dict[str, Any],
    sighting_b: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze timeline continuity between two sightings or report + found record.
    Both sighting dictionaries contain:
    - location: place name or description
    - lat, lon: coordinates (optional)
    - timestamp: ISO string or datetime
    - direction: direction string
    - observed_by: observer role / facility
    """
    coord_a = get_coordinates(sighting_a.get("location", ""), sighting_a.get("lat"), sighting_a.get("lon"))
    coord_b = get_coordinates(sighting_b.get("location", ""), sighting_b.get("lat"), sighting_b.get("lon"))
    
    time_a = parse_timestamp(sighting_a.get("timestamp"))
    time_b = parse_timestamp(sighting_b.get("timestamp"))
    
    # Distance in km
    distance_km = haversine_distance(coord_a, coord_b)
    
    # Time difference in minutes and hours
    delta_seconds = abs((time_b - time_a).total_seconds())
    delta_minutes = delta_seconds / 60.0
    delta_hours = delta_seconds / 3600.0
    
    # Determine sequence order
    is_chronological = time_b >= time_a
    first_sight = sighting_a if is_chronological else sighting_b
    second_sight = sighting_b if is_chronological else sighting_a
    
    # Estimated velocity in km/h
    # Prevent division by zero
    effective_hours = max(delta_hours, 1.0 / 60.0)  # at least 1 minute
    implied_speed_kmh = distance_km / effective_hours
    
    # Direction alignment
    dir_alignment = calculate_direction_alignment(
        sighting_a.get("direction", ""),
        sighting_b.get("direction", "")
    )
    
    # Velocity Plausibility & Conflict Checks
    # Walking speed in disaster terrain: 1-5 km/h
    # Vehicle / ambulance transport: up to 60 km/h
    # Implausible speed: > 90 km/h (teleportation/conflict)
    is_speed_impossible = implied_speed_kmh > 90.0 and distance_km > 5.0
    is_speed_suspicious = implied_speed_kmh > 55.0 and distance_km > 3.0
    
    # Continuity score calculation (0.0 to 1.0)
    if is_speed_impossible:
        continuity_score = 0.0
        conflict_flag = True
        conflict_reason = (f"Impossible travel speed: {distance_km:.1f} km traveled in "
                           f"{delta_minutes:.0f} mins ({implied_speed_kmh:.0f} km/h) between sightings")
    elif distance_km <= 0.5 and delta_minutes <= 45:
        # Very close in time and location
        continuity_score = 0.95 * (0.8 + 0.2 * dir_alignment)
        conflict_flag = False
        conflict_reason = None
    elif distance_km <= 3.0 and delta_minutes <= 120 and implied_speed_kmh <= 10.0:
        # Realistic walking track
        continuity_score = 0.85 * (0.7 + 0.3 * dir_alignment)
        conflict_flag = False
        conflict_reason = None
    elif distance_km <= 15.0 and delta_hours <= 12 and implied_speed_kmh <= 45.0:
        # Realistic vehicular / emergency transit
        continuity_score = 0.70 * (0.7 + 0.3 * dir_alignment)
        conflict_flag = False
        conflict_reason = None
    elif delta_hours > 72:
        # Large time gap - low certainty but not impossible
        continuity_score = 0.40
        conflict_flag = False
        conflict_reason = None
    else:
        # Moderate continuity
        continuity_score = max(0.2, 0.6 - (distance_km / 50.0)) * (0.7 + 0.3 * dir_alignment)
        conflict_flag = is_speed_suspicious
        conflict_reason = (f"Unusually fast transit ({implied_speed_kmh:.0f} km/h) across disaster zone"
                           if is_speed_suspicious else None)

    return {
        "distance_km": round(distance_km, 2),
        "delta_minutes": round(delta_minutes, 1),
        "delta_hours": round(delta_hours, 2),
        "implied_speed_kmh": round(implied_speed_kmh, 1),
        "direction_alignment": round(dir_alignment, 3),
        "direction_a": sighting_a.get("direction", "Unknown"),
        "direction_b": sighting_b.get("direction", "Unknown"),
        "is_chronological": is_chronological,
        "first_location": first_sight.get("location", ""),
        "second_location": second_sight.get("location", ""),
        "continuity_score": round(continuity_score, 3),
        "conflict_flag": conflict_flag,
        "conflict_reason": conflict_reason,
        "supporting_note": (
            f"Location continuity consistent: {distance_km:.1f} km apart within {delta_minutes:.0f} mins "
            f"(movement speed ~{implied_speed_kmh:.1f} km/h, direction: {sighting_a.get('direction', 'N/A')})"
            if continuity_score >= 0.6 and not conflict_flag else None
        )
    }

