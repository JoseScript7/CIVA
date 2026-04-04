"""Geolocation and Real-Time Threat Mapping Module."""

import math
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class GeoLocation:
    """Real-time geographic coordinates and metadata."""
    country: str
    city: str
    latitude: float
    longitude: float
    asn: str = ""
    isp: str = ""
    vpn_detected: bool = False
    proxy_detected: bool = False


class GeoThreatMapper:
    """
    Maps attack locations in real-time for dashboard visualization.
    Calculates impossible travel distances and velocity anomalies.
    """
    
    # Known hacker origin countries/ASNs for risk scoring
    RISKY_COUNTRIES = {"KP", "IR", "CN", "RU", "BY", "SY"}  # High-risk jurisdictions
    RISKY_ASNS = {
        "AS3352",  # Telefonica (known botnet concentration)
        "AS36692", # OpenBNG
        "AS9009",  # M247
        "AS8452",  # Tedata
    }
    
    def __init__(self):
        self.user_locations: Dict[str, GeoLocation] = {}
        self.attack_heatmap: Dict[str, int] = {}  # Country -> attack count
        
    def calculate_distance(self, 
                          lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
        """Calculate geodesic distance between two points (km)."""
        R = 6371  # Earth radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def detect_impossible_travel(self,
                                 user_id: str,
                                 new_location: GeoLocation,
                                 time_delta_seconds: int) -> Tuple[bool, float]:
        """
        Detect impossible travel: 
        - Is the new location too far given the time delta?
        - Returns: (is_anomalous, velocity_kmh)
        """
        if user_id not in self.user_locations:
            self.user_locations[user_id] = new_location
            return False, 0.0
        
        old_loc = self.user_locations[user_id]
        
        # Calculate distance
        distance_km = self.calculate_distance(
            old_loc.latitude, old_loc.longitude,
            new_location.latitude, new_location.longitude
        )
        
        # Calculate required velocity
        if time_delta_seconds < 1:
            time_delta_seconds = 1
        
        velocity_kmh = (distance_km / time_delta_seconds) * 3600
        
        # Human max speed: ~900 km/h (max commercial flight)
        # Realistic max: ~600 km/h (considers connection time)
        is_anomalous = velocity_kmh > 900
        
        # Update user location
        self.user_locations[user_id] = new_location
        
        return is_anomalous, velocity_kmh
    
    def calculate_country_risk_score(self, country: str, asn: str = "") -> float:
        """Calculate risk score (0-1) based on geolocation."""
        risk = 0.0
        
        # Country-based risk
        if country in self.RISKY_COUNTRIES:
            risk += 0.5
        
        # ASN-based risk
        if asn in self.RISKY_ASNS:
            risk += 0.3
        
        # Add to attack heatmap
        self.attack_heatmap[country] = self.attack_heatmap.get(country, 0) + 1
        
        return min(risk, 1.0)
    
    def generate_heatmap_data(self) -> Dict[str, int]:
        """Generate heatmap for dashboard — country -> attack count."""
        return self.attack_heatmap.copy()
    
    def get_top_attack_sources(self, limit: int = 10) -> list:
        """Get top attack-origin countries."""
        sorted_countries = sorted(
            self.attack_heatmap.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_countries[:limit]
    
    def calculate_travel_risk_score(self,
                                    user_id: str,
                                    new_location: GeoLocation,
                                    time_delta_seconds: int) -> float:
        """
        Calculate combined travel risk score (0-100).
        Combines impossible travel + country risk.
        """
        is_impossible, velocity = self.detect_impossible_travel(
            user_id, new_location, time_delta_seconds
        )
        
        country_risk = self.calculate_country_risk_score(
            new_location.country, new_location.asn
        )
        
        travel_score = 0.0
        
        if is_impossible:
            # Normalize velocity: 900 km/h = 50 points, 1800+ = 100 points
            travel_score = min((velocity / 1800.0) * 100, 100)
        
        if new_location.vpn_detected:
            travel_score += 20
        
        if new_location.proxy_detected:
            travel_score += 15
        
        # Combine with country risk
        final_score = (travel_score * 0.6) + (country_risk * 40)
        
        return min(final_score, 100.0)


class DashboardLocationRenderer:
    """Generates dashboard-ready location data for maps."""
    
    def __init__(self, geo_mapper: GeoThreatMapper):
        self.mapper = geo_mapper
        self.attack_timeline = []  # Time-series of attacks
        
    def render_attack_marker(self, 
                            attack_id: str,
                            location: GeoLocation,
                            severity: float,
                            attack_type: str) -> Dict:
        """Generate a marker for Mapbox/Leaflet dashboard."""
        return {
            "id": attack_id,
            "type": "Feature",
            "properties": {
                "title": f"{attack_type} - Risk: {severity:.1f}%",
                "severity": severity,
                "attack_type": attack_type,
                "country": location.country,
                "city": location.city,
                "vpn": location.vpn_detected,
                "proxy": location.proxy_detected,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [location.longitude, location.latitude]
            }
        }
    
    def render_geofence(self, 
                       user_baseline_location: GeoLocation,
                       radius_km: float = 50) -> Dict:
        """Generate a geofence circle for expected user location."""
        # Approximate 1 degree latitude ≈ 111 km
        lat_offset = radius_km / 111.0
        # Longitude offset varies by latitude
        lon_offset = radius_km / (111.0 * math.cos(math.radians(user_baseline_location.latitude)))
        
        return {
            "type": "Feature",
            "properties": {
                "name": "User Geofence",
                "radius_km": radius_km,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [user_baseline_location.longitude - lon_offset, 
                     user_baseline_location.latitude - lat_offset],
                    [user_baseline_location.longitude + lon_offset, 
                     user_baseline_location.latitude - lat_offset],
                    [user_baseline_location.longitude + lon_offset, 
                     user_baseline_location.latitude + lat_offset],
                    [user_baseline_location.longitude - lon_offset, 
                     user_baseline_location.latitude + lat_offset],
                    [user_baseline_location.longitude - lon_offset, 
                     user_baseline_location.latitude - lat_offset],
                ]]
            }
        }
    
    def render_heatmap(self) -> Dict:
        """Generate heatmap layer data."""
        heatmap_data = self.mapper.generate_heatmap_data()
        
        # Convert country -> attack count to GeoJSON heatmap
        features = []
        for country, count in heatmap_data.items():
            # Rough country centroids (simplified)
            country_coords = self._get_country_center(country)
            if country_coords:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "country": country,
                        "attack_count": count,
                        "intensity": min(count / 100, 1.0),  # Normalize 0-1
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": country_coords
                    }
                })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def _get_country_center(self, country_code: str) -> Optional[Tuple[float, float]]:
        """Return approximate center coordinates for a country."""
        # Simplified country centroids
        centroids = {
            "RU": [105.3188, 61.5240],    # Russia
            "CN": [104.1954, 35.8617],    # China
            "US": [-95.7129, 37.0902],    # USA
            "GB": [-3.4360, 55.3781],     # UK
            "DE": [10.4515, 51.1657],     # Germany
            "RO": [24.9668, 45.9432],     # Romania
            "UA": [31.1656, 48.3794],     # Ukraine
            "PK": [69.3451, 30.3753],     # Pakistan
            "NG": [8.6753, 9.0820],       # Nigeria
            "JP": [138.2529, 36.2048],    # Japan
            "IN": [78.9629, 20.5937],     # India
        }
        return centroids.get(country_code)
    
    def render_attack_timeline_chart(self) -> Dict:
        """Generate time-series data for attack timeline chart."""
        return {
            "type": "time-series",
            "data_points": self.attack_timeline,
            "metrics": {
                "total_attacks": len(self.attack_timeline),
                "unique_sources": len(set(a["country"] for a in self.attack_timeline)),
                "top_attack_type": "credential_spray",  # Most common
            }
        }


# Example usage in behavior-agent API response
def enrich_behavior_score_with_geolocation(score_response: Dict,
                                          location: GeoLocation) -> Dict:
    """Add geolocation data to risk score response."""
    geo_mapper = GeoThreatMapper()
    
    # Calculate travel-based risk
    travel_risk = geo_mapper.calculate_travel_risk_score(
        user_id=score_response.get("user_id", ""),
        new_location=location,
        time_delta_seconds=60  # Example: 60s since last event
    )
    
    # Combine with ML risk score
    ml_risk = score_response.get("final_risk_score", 0)
    combined_risk = (ml_risk * 0.6) + (travel_risk * 0.4)
    
    # Add geolocation data
    score_response["geolocation"] = {
        "country": location.country,
        "city": location.city,
        "coordinates": {
            "latitude": location.latitude,
            "longitude": location.longitude
        },
        "vpn_detected": location.vpn_detected,
        "proxy_detected": location.proxy_detected,
        "travel_risk_score": travel_risk,
        "combined_risk_score": combined_risk,
    }
    
    return score_response
