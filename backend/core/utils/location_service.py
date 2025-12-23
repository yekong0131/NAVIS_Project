# core/utils/location_service.py

from typing import Optional, Tuple
from math import radians, cos, sin, asin, sqrt


def get_coordinates_from_port(port_name: str) -> Optional[Tuple[float, float]]:
    """
    항구 이름으로 좌표 조회

    Args:
        port_name: "부산항", "통영항" 등

    Returns:
        (lat, lon) 튜플 또는 None
    """
    from core.models import Port

    if not port_name:
        return None

    # 정확히 일치하는 항구 찾기
    port = Port.objects.filter(port_name__iexact=port_name).first()

    if port:
        print(f"[Port] 항구 찾음: {port.port_name} ({port.lat}, {port.lon})")
        return (port.lat, port.lon)

    # 부분 일치 찾기
    port = Port.objects.filter(port_name__icontains=port_name).first()

    if port:
        print(f"[Port] 항구 찾음 (부분일치): {port.port_name} ({port.lat}, {port.lon})")
        return (port.lat, port.lon)

    print(f"[Port] [Warning]  항구를 찾을 수 없음: {port_name}")
    return None


def find_nearest_port(
    lat: float, lon: float, max_distance_km: float = 50
) -> Optional[str]:
    """
    좌표로 가장 가까운 항구 찾기

    Args:
        lat, lon: 사용자 좌표
        max_distance_km: 최대 거리 (km)

    Returns:
        항구 이름 또는 None
    """
    from core.models import Port

    def haversine(lat1, lon1, lat2, lon2):
        """두 좌표 간의 거리(km) 계산"""
        R = 6371  # 지구 반지름 (km)

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        return R * c

    ports = Port.objects.all()
    if not ports:
        return None

    nearest_port = None
    min_distance = float("inf")

    for port in ports:
        distance = haversine(lat, lon, port.lat, port.lon)
        if distance < min_distance:
            min_distance = distance
            nearest_port = port

    # 최대 거리 이내의 항구만 반환
    if min_distance <= max_distance_km:
        print(
            f"[Port] 가장 가까운 항구: {nearest_port.port_name} ({min_distance:.1f}km)"
        )
        return nearest_port.port_name

    print(f"[Port] [Warning]  {max_distance_km}km 이내에 항구 없음")
    return None
