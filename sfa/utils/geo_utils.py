import math
from typing import Tuple, Optional, List, Dict, Any


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two GPS coordinates using Haversine formula.
    
    Args:
        lat1, lng1: First point coordinates
        lat2, lng2: Second point coordinates
    
    Returns:
        Distance in meters
    """
    R = 6371e3  # Earth's radius in meters
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)

    a = math.sin(Δφ/2) * math.sin(Δφ/2) + \
        math.cos(φ1) * math.cos(φ2) * \
        math.sin(Δλ/2) * math.sin(Δλ/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two GPS coordinates and return in kilometers.
    
    Args:
        lat1, lng1: First point coordinates
        lat2, lng2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    distance_meters = calculate_distance(lat1, lng1, lat2, lng2)
    return distance_meters / 1000


def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate if coordinates are within valid ranges.
    
    Args:
        lat: Latitude (-90 to 90)
        lng: Longitude (-180 to 180)
    
    Returns:
        True if valid, False otherwise
    """
    return -90 <= lat <= 90 and -180 <= lng <= 180


def format_distance(distance_meters: float, precision: int = 1) -> str:
    """Format distance in meters to readable string.
    
    Args:
        distance_meters: Distance in meters
        precision: Decimal places for formatting
    
    Returns:
        Formatted distance string (e.g., "2.5 km", "150 m")
    """
    if distance_meters < 1000:
        return f"{round(distance_meters)} m"
    else:
        distance_km = distance_meters / 1000
        return f"{round(distance_km, precision)} km"


def optimize_route(customers: List[Dict], user_lat: float, user_lng: float) -> List[Dict]:
    """Optimize customer visit route using nearest neighbor algorithm"""
    if not customers or len(customers) <= 1:
        return customers
    
    # Create a copy to avoid modifying original list
    unvisited = customers.copy()
    optimized_route = []
    
    # Start from user's location
    current_lat, current_lng = user_lat, user_lng
    
    while unvisited:
        # Find the nearest unvisited customer
        nearest_customer = None
        min_distance = float('inf')
        nearest_index = -1
        
        for i, customer in enumerate(unvisited):
            customer_lat = customer.get('latitude')
            customer_lng = customer.get('longitude')
            
            if customer_lat and customer_lng:
                try:
                    customer_lat = float(customer_lat)
                    customer_lng = float(customer_lng)
                    distance = calculate_distance(current_lat, current_lng, customer_lat, customer_lng)
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_customer = customer
                        nearest_index = i
                except (ValueError, TypeError):
                    continue
        
        # If no valid coordinates found, add remaining customers as-is
        if nearest_customer is None:
            optimized_route.extend(unvisited)
            break
        
        # Add nearest customer to route and update current position
        optimized_route.append(nearest_customer)
        current_lat = float(nearest_customer.get('latitude'))
        current_lng = float(nearest_customer.get('longitude'))
        unvisited.pop(nearest_index)
    
    return optimized_route


def calculate_route_stats(customers: List[Dict], user_lat: float, user_lng: float) -> Dict[str, Any]:
    """Calculate route statistics including total distance and estimated time"""
    if not customers:
        return {
            "total_distance_km": 0.0,
            "total_distance_formatted": "0 m",
            "estimated_time_minutes": 0,
            "estimated_time_formatted": "0 min"
        }
    
    total_distance_meters = 0
    current_lat, current_lng = user_lat, user_lng
    
    for customer in customers:
        customer_lat = customer.get('latitude')
        customer_lng = customer.get('longitude')
        
        if customer_lat and customer_lng:
            try:
                customer_lat = float(customer_lat)
                customer_lng = float(customer_lng)
                distance = calculate_distance(current_lat, current_lng, customer_lat, customer_lng)
                total_distance_meters += distance
                current_lat, current_lng = customer_lat, customer_lng
            except (ValueError, TypeError):
                continue
    
    total_distance_km = total_distance_meters / 1000
    estimated_time_minutes = int((total_distance_km / 30) * 60) + (len(customers) * 15)  # 30 km/h + 15 min per customer
    
    return {
        "total_distance_km": round(total_distance_km, 1),
        "total_distance_formatted": format_distance(total_distance_meters),
        "estimated_time_minutes": estimated_time_minutes,
        "estimated_time_formatted": f"{estimated_time_minutes} min" if estimated_time_minutes < 60 else f"{estimated_time_minutes // 60}h {estimated_time_minutes % 60}m"
    }
