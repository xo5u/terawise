import csv
import json
import os


def csv_to_json(csv_file_path, json_file_path):
  if not os.path.exists(csv_file_path):
    print(f"Warning: '{csv_file_path}' not found, skipped.")
    return

  data = []

  with open(csv_file_path, mode="r", encoding="utf-8-sig") as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
      data.append(row)

  with open(json_file_path, mode="w", encoding="utf-8") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

  print(f"Converted '{csv_file_path}' to '{json_file_path}'")


def main():
  files_to_convert = [
      "rain_monthly.csv",
      "ph_soil.csv",
      "temperature_monthly_estimate.csv",
  ]

  for csv_file in files_to_convert:
    json_file = csv_file.rsplit(".", 1)[0] + ".json"
    csv_to_json(csv_file, json_file)


if __name__ == "__main__":
  main()