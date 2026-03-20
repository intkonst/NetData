import csv
import requests
import time
from pathlib import Path

# --- НАСТРОЙКИ ---
API_KEY = "de2b5756-a2de-47a6-83c6-5fdc401d626a"
INPUT_FILE = "data.csv"
OUTPUT_FILE = "data_with_coords.csv"
# -----------------

def get_coords(address, api_key):
    base_url = "https://geocode-maps.yandex.ru/v1/"
    params = {
        "apikey": api_key,
        "geocode": address,
        "format": "json"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        feature_member = data['response']['GeoObjectCollection']['featureMember']
        
        if feature_member:
            coords = feature_member[0]['GeoObject']['Point']['pos']
            return coords 
        return "not_found"
    
    except Exception as e:
        print(f"Ошибка при запросе адреса {address}: {e}")
        return "error"

def process_csv():
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"Файл {INPUT_FILE} не найден!")
        return

    with open(input_path, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    print(f"Найдено строк: {len(rows)}. Начинаю геокодирование...")

    with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        
        for index, row in enumerate(rows):

            if len(row) < 2:
                writer.writerow(row + ["", ""])
                continue

            address_to_geocode = row[1]
            print(f"[{index + 1}/{len(rows)}] Обработка: {address_to_geocode}")

            full_coords = get_coords(address_to_geocode, API_KEY)
            
            if full_coords not in ["not_found", "error"]:
                lon, lat = full_coords.split(" ")
            else:
                lon, lat = "", ""

            writer.writerow(row + [lon, lat])
            
            time.sleep(0.1)

    print(f"Готово! Результат сохранен в {OUTPUT_FILE}")

if __name__ == "__main__":
    process_csv()