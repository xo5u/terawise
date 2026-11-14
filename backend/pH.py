
import requests

API_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"

# Test location: California, USA
LAT = 37.368402
LON = -121.771


def get_soil_ph(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid latitude or longitude")

    query = f"""
    SELECT TOP 20
        mu.muname AS soil_name,
        c.compname AS component,
        c.comppct_r AS component_percent,
        ch.hzdept_r AS depth_top_cm,
        ch.hzdepb_r AS depth_bottom_cm,
        ch.ph1to1h2o_r AS ph
    FROM mapunit mu
    INNER JOIN component c ON mu.mukey = c.mukey
    INNER JOIN chorizon ch ON c.cokey = ch.cokey
    WHERE mu.mukey IN (
        SELECT mukey
        FROM SDA_Get_Mukey_from_intersection_with_WktWgs84(
            'POINT({lon} {lat})'
        )
    )
    AND c.majcompflag = 'Yes'
    AND ch.ph1to1h2o_r IS NOT NULL
    ORDER BY c.comppct_r DESC, ch.hzdept_r ASC
    """

    response = requests.post(
        API_URL,
        data={
            "query": query,
            "format": "JSON+COLUMNNAME"
        },
        timeout=90
    )

    response.raise_for_status()
    data = response.json()

    table = data.get("Table", [])

    if len(table) < 2:
        return []

    headers = table[0]
    rows = table[1:]

    return [dict(zip(headers, row)) for row in rows]


try:
    results = get_soil_ph(LAT, LON)

    if not results:
        print("No soil pH data found for this location.")
    else:
        for item in results:
            print(
                f"Soil: {item['soil_name']} | "
                f"Depth: {item['depth_top_cm']}-{item['depth_bottom_cm']} cm | "
                f"pH: {item['ph']}"
            )

except requests.RequestException as error:
    print("API request failed:", error)
except (ValueError, KeyError) as error:
    print("Data error:", error)
