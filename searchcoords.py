import requests
import json

def main():

    base_url = "http://127.0.0.1:8000"

    token = "cXeCObwiqJanLzMAOD6URUkWyV5nLCm8naeotWhqKtk" 

    print("=== NetData API Coords Client ===")
    print(f"Подключение к: {base_url}/coords")
    
    while True:
        print("\n--- Новый запрос ---")
        user_input = input("Введите параметры через пробел (широта долгота радиус_в_км) или 'exit': ")
        
        if user_input.lower() in ['exit', 'quit', 'выход']:
            break

        try:
    
            parts = user_input.split()
            if len(parts) < 3:
                print("[!] Ошибка: Нужно ввести 3 числа: lat, lon и radius. Пример: 55.808 37.537 0.5")
                continue
                
            lat = float(parts[0])
            lon = float(parts[1])
            radius = float(parts[2])


            payload = {
                "lat": lat,
                "lon": lon,
                "radius": radius
            }
            
            headers = {
                "X-Token": token,
                "Content-Type": "application/json"
            }

            print(f"\n[ОТПРАВЛЕНО] POST /coords")
            print(f"Параметры: {json.dumps(payload, indent=2)}")


            response = requests.post(
                f"{base_url}/coords", 
                json=payload, 
                headers=headers
            )
            

            print(f"[СТАТУС ОТВЕТА] {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"[ПОЛУЧЕНО]: Найдено объектов: {result.get('count_found', 0)}")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"[ОШИБКА] Сервер вернул: {response.text}")

        except ValueError:
            print("[!] Ошибка: Вводите только числа. Пример: 55.808 37.537 0.5")
        except requests.exceptions.ConnectionError:
            print("[ОШИБКА] Не удалось подключиться к серверу. Убедитесь, что API запущено.")
        except Exception as e:
            print(f"[ОШИБКА] Произошла ошибка: {e}")

if __name__ == "__main__":
    main()