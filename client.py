import requests

# Адрес сервера (проверь порт в конфиге сервера, по умолчанию в коде 8000)
BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("--- Начинаем проверку API ---")

    print("\n[1] Проверка статуса (GET /health):")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Статус-код: {response.status_code}")
        print(f"Ответ: {response.json()}")
    except Exception as e:
        print(f"Ошибка при подключении: {e}")

    print("\n[2] Получение информации (GET /info):")
    response = requests.get(f"{BASE_URL}/info")
    print(f"Статус-код: {response.status_code}")
    print(f"Ответ: {response.json()}")

    print("\n[3] Отправка данных (POST /data):")
    test_data = {"sensor": "temperature", "value": 25.5, "unit": "Celsius"}
    response = requests.post(f"{BASE_URL}/data", json=test_data)
    print(f"Статус-код: {response.status_code}")
    print(f"Ответ от сервера: {response.json()}")


    print("\n[4.1] Тест валидации регистрации (некорректный пароль):")
    bad_user = {
        "login": "admin",
        "password": "123", 
        "email": "invalid-email"
    }
    response = requests.post(f"{BASE_URL}/register", json=bad_user)
    print(f"Статус-код: {response.status_code}")
    print(f"Ответ: {response.json()}")

   
    print("\n[4.2] Тест успешной регистрации:")

    import time
    unique_login = f"user_{int(time.time())}"
    
    good_user = {
        "login": unique_login,
        "password": "Testpassword123!",
        "email": "konstantinovalex38@gmail.com"
    }
    response = requests.post(f"{BASE_URL}/register", json=good_user)
    print(f"Статус-код: {response.status_code}")
    print(f"Ответ: {response.json()}")

if __name__ == "__main__":
    test_api()