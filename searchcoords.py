import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print as rprint

def main():
    console = Console()
    base_url = "http://127.0.0.1:8000"

    # Красивый заголовок
    console.print(Panel.fit(
        "[bold cyan]NetData API Coords Client[/bold cyan]\n"
        "[white]Инструмент для поиска объектов по координатам и радиусу[/white]",
        border_style="cyan"
    ))

    # Ручной ввод токена
    rprint("[yellow]Совет:[/yellow] Токен можно найти в письме после регистрации в системе.")
    token = Prompt.ask("[bold green]Введите ваш API токен[/bold green]")

    if not token:
        console.print("[red]Ошибка: Токен не может быть пустым![/red]")
        return

    console.print(f"\n[bold]Подключение к:[/bold] [underline]{base_url}[/underline]\n")
    console.print("[blue]Подсказка: Для теста попробуйте ввести:[/blue] [bold white]55.8083 37.537 0.1[/bold white]")

    while True:
        user_input = Prompt.ask("\n[bold]Введите параметры через пробел (широта долгота радиус_в_км)[/bold] (или [red]'exit'[/red])")
        
        if user_input.lower() in ['exit', 'quit', 'выход']:
            console.print("[yellow]Завершение работы клиента...[/yellow]")
            break

        try:
            parts = user_input.split()
            if len(parts) < 3:
                console.print("[bold red][!] Ошибка:[/bold red] Нужно ввести 3 числа: lat, lon и radius. Пример: 55.8083 37.537 0.1")
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

            # Анимация загрузки во время запроса
            with console.status("[bold green]Запрос к API /coords...") as status:
                response = requests.post(
                    f"{base_url}/coords", 
                    json=payload, 
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    console.print("\n[bold green]✅ Ответ получен:[/bold green]")
                    console.print(f"[bold cyan]Найдено объектов:[/bold cyan] [bold white]{result.get('count_found', 0)}[/bold white]")
                    
                    # Красивый вывод JSON
                    console.print_json(data=result)
                    
                elif response.status_code == 403:
                    console.print(f"[bold red]❌ Ошибка 403:[/bold red] {response.json().get('detail', 'Доступ запрещен')}")
                elif response.status_code == 422:
                    console.print(f"[bold red]❌ Ошибка 422 (Неверный формат данных):[/bold red]")
                    console.print_json(data=response.json())
                else:
                    console.print(f"[bold red]❌ Ошибка {response.status_code}:[/bold red] {response.text}")

        except ValueError:
            console.print("[bold red][!] Ошибка:[/bold red] Вводите только числа. Пример: [bold white]55.8083 37.537 0.1[/bold white]")
        except requests.exceptions.ConnectionError:
            console.print("[bold red]❌ Ошибка:[/bold red] Не удалось подключиться к серверу. Убедитесь, что API на FastAPI/Uvicorn запущено.")
        except Exception as e:
            console.print(f"[bold red]❌ Непредвиденная ошибка:[/bold red] {e}")

if __name__ == "__main__":
    main()