import requests
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


console = Console()
BASE_URL = "http://127.0.0.1:8000"

def print_step(number, title):
    console.print(f"\n[bold yellow]Этап {number}: {title}[/bold yellow]")

def wait_for_user(next_test_name=""):
    suffix = f" (след. тест: {next_test_name})" if next_test_name else ""
    Prompt.ask(f"\n[dim]Нажмите Enter, чтобы продолжить{suffix}[/dim]")

def test_api():
    console.print(Panel("[bold cyan]API NetData: ПОЛНЫЙ ЦИКЛ ТЕСТИРОВАНИЯ[/bold cyan]", expand=False))

    print_step(1, "Проверка доступности (GET /health)")
    try:
        response = requests.get(f"{BASE_URL}/health")
        console.print_json(data=response.json())
        wait_for_user("/info")
    except Exception as e:
        console.print(Panel(f"[bold red]Ошибка соединения![/bold red]\n{e}", title="Error"))
        return

    print_step(2, "Получение информации (GET /info)")
    try:
        response = requests.get(f"{BASE_URL}/info")
        console.print_json(data=response.json())
        wait_for_user("/register [error test]")
    except Exception as e:
        console.print(f"[bold red]Ошибка при получении /info: {e}[/bold red]")

    print_step(3, "Тест некорректной регистрации")
    bad_reg_data = {
        "login": "inv", 
        "password": "123", 
        "email": "wrong-email-format"
    }
    console.print("[bold blue]Отправляем некорректный JSON на регистрацию:[/bold blue]")
    console.print_json(data=bad_reg_data)
    
    response = requests.post(f"{BASE_URL}/register", json=bad_reg_data)
    console.print("[bold green]Ответ сервера (ожидаемые ошибки):[/bold green]")
    console.print_json(data=response.json())
    wait_for_user("/register [custom test]")

    print_step(4, "Настройка учетных данных")
    default_login = f"user_{int(time.time())}"
    default_pass = "TestPassword123!"
    
    user_login = Prompt.ask(f"Введите логин для теста", default=default_login)
    user_password = Prompt.ask(f"Введите пароль для теста", default=default_pass, password=True)
    user_email = Prompt.ask(f"Введите email для уведомлений", default="konstantinovalex38@gmail.com")



    print_step(5, "Регистрация пользователя")
    reg_data = {"login": user_login, "password": user_password, "email": user_email}
    
    console.print("[bold blue]Отправляем JSON на регистрацию:[/bold blue]")
    console.print_json(data=reg_data)
    
    with console.status("[bold green]Регистрация..."):
        response = requests.post(f"{BASE_URL}/register", json=reg_data)
    
    res_reg = response.json()
    console.print("[bold green]Ответ сервера:[/bold green]")
    console.print_json(data=res_reg)

    if res_reg.get("status") == "success" or "already exists" in str(res_reg.get("message", "")):
        
        if res_reg.get("status") == "success":
            console.print(Panel(f"ЛОГИН: [bold]{user_login}[/bold]\nПАРОЛЬ: [bold]{user_password}[/bold]", title="Данные для верификации"))
            console.print("\n[blink bold red]ВНИМАНИЕ![/blink bold red] Подтвердите почту по ссылке.")
            Prompt.ask("[bold yellow]Нажмите Enter после верификации (след. тест: /login)[/bold yellow]")
        else:
            console.print("[yellow]Пользователь уже существует, пробуем сразу логин...[/yellow]")
            wait_for_user("/login")

        print_step(6, "Авторизация и получение токена")
        login_data = {"login": user_login, "password": user_password}
        
        console.print("[bold blue]Отправляем JSON для входа:[/bold blue]")
        console.print_json(data=login_data)
        
        with console.status("[bold blue]Вход..."):
            response = requests.post(f"{BASE_URL}/login", json=login_data)
        
        res_login = response.json()
        console.print("[bold green]Ответ сервера:[/bold green]")
        console.print_json(data=res_login)
        wait_for_user("/data [final test]")

        if res_login.get("status") == "success":

            print_step(7, "Тестирование API-токена (POST /data)")
            console.print("[bold magenta]Зайдите в почту и скопируйте ваш новый API-токен.[/bold magenta]")
            api_token = Prompt.ask("Вставьте API-токен для проверки")

            test_payload = {"sensor": "terminal_test", "value": 42.0}
            headers = {"X-Token": api_token}

            console.print("[bold blue]Отправляем данные с токеном в заголовке X-Token:[/bold blue]")
            console.print_json(data=test_payload)

            with console.status("[bold cyan]Проверка доступа..."):
                res_data = requests.post(f"{BASE_URL}/data", json=test_payload, headers=headers)
            
            console.print("[bold green]Ответ сервера:[/bold green]")
            if res_data.status_code == 200:
                console.print_json(data=res_data.json())
                console.print("\n[bold green]✓ ТЕСТ ПРОЙДЕН: Токен валиден, доступ разрешен![/bold green]")
            else:
                console.print(f"[bold red]✗ ОШИБКА ДОСТУПА: Статус {res_data.status_code}[/bold red]")
                console.print_json(data=res_data.json())
        else:
            console.print("\n[bold red]✗ Ошибка при логине. Тест токена невозможен.[/bold red]")
            
    else:
        console.print("[bold red]Регистрация не удалась.[/bold red]")

    console.print("\n[bold cyan]=== Конец теста ===[/bold cyan]")

if __name__ == "__main__":
    test_api()