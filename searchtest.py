import requests
import json

def main():

    base_url = "http://127.0.0.1:8000"

    token = "cXeCObwiqJanLzMAOD6URUkWyV5nLCm8naeotWhqKtk" 

    print("=== NetData API Client ===")
    print(f"Подключение к: {base_url}")
    
    while True:

        user_query = input("\nВведите адрес для поиска (или 'exit' для выхода): ")
        
        if user_query.lower() in ['exit', 'quit', 'выход']:
            break

        payload = {
            "address_query": user_query
        }
        
        headers = {
            "X-Token": token,
            "Content-Type": "application/json"
        }

        print(f"\n[ОТПРАВЛЕНО] POST /search")
        print(f"Данные: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        try:

            response = requests.post(
                f"{base_url}/search", 
                json=payload, 
                headers=headers
            )
            

            print(f"[СТАТУС ОТВЕТА] {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("[ПОЛУЧЕНО]:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"[ОШИБКА] Что-то пошло не так: {response.text}")

        except requests.exceptions.ConnectionError:
            print("[ОШИБКА] Не удалось подключиться к серверу. Убедитесь, что API запущено.")
        except Exception as e:
            print(f"[ОШИБКА] Произошла непредвиденная ошибка: {e}")

if __name__ == "__main__":
    main()