import csv
import re

import requests

API_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"

# Test location: California, USA
LAT = 37.368402
LON = -121.771


def clean_soil_name(name):
    """Remove slope info and MLRA from the soil name."""
    name = re.sub(r",?\s*MLRA\s*\d+[A-Za-z]*", "", name)
    name = re.sub(r",?\s*[\d.]+\s*to\s*[\d.]+\s*percent\s*slopes?", "", name)
    name = re.sub(r",?\s*[\d.]+\s*percent\s*slopes?", "", name)
    return name.strip(" ,")


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

    results = [dict(zip(headers, row)) for row in rows]
    return filter_relevant_depths(results)

def filter_relevant_depths(results):
    """
    Keep only the two most relevant soil layers:
    1. Surface layer (fertilizer zone ~0-20 cm)
    2. Next layer (around average root depth)
    """
    relevant = []

    for item in results:
        try:
            top = float(item["depth_top_cm"])
            bottom = float(item["depth_bottom_cm"])
        except (TypeError, ValueError):
            continue

        # Layer 1:fertilizer (0-20 cm)
        if top <= 5 and bottom <= 25:
            relevant.append(item)

        # Layer 2: Upper root zone (15-40 cm)
        elif top >= 10 and top <= 25 and bottom <= 50:
            relevant.append(item)

    # Keep maximum 2 results
    return relevant[:2]


def save_csv(rows, filename="ph_soil.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["soil", "depth_top_cm", "depth_bottom_cm", "ph"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return filename


try:
    results = get_soil_ph(LAT, LON)

    if not results:
        print("No soil pH data found for this location.")
    else:
        rows = []
        for item in results:
            row = {
                "soil": clean_soil_name(item["soil_name"]),
                "depth_top_cm": item["depth_top_cm"],
                "depth_bottom_cm": item["depth_bottom_cm"],
                "ph": item["ph"],
            }
            rows.append(row)
            print(
                f"Soil: {row['soil']} | "
                f"Depth: {row['depth_top_cm']}-{row['depth_bottom_cm']} cm | "
                f"pH: {row['ph']}"
            )

        print(f"\nSaved: {save_csv(rows)}")

except requests.RequestException as error:
    print("API request failed:", error)
except (ValueError, KeyError) as error:
    print("Data error:", error)





