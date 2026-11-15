import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent / ".env")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

print("Connected to Supabase!")

response = supabase.table("crops").select("name").execute()

print("Total rows:", len(response.data))
print("Data:", response.data)

for crop in response.data:
    print("Crop name:", crop["name"])