
import httpx


async def get_region_name(lat: float, lng: float):

    url = "https://nominatim.openstreetmap.org/reverse"

    params = {
        "lat": lat,
        "lon": lng,
        "format": "jsonv2",
        "addressdetails": 1
    }

    headers = {
        "User-Agent": "Terawise/1.0 (location service)"
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            url,
            params=params,
            headers=headers
        )

        response.raise_for_status()
        data = response.json()

    address = data.get("address", {})

    region = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or address.get("state")
    )

    if not region:
        return None

    return {
        "lat": lat,
        "lng": lng,
        "region": region,
        "country": address.get("country"),
        "display_name": data.get("display_name")
    }
