import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import print as rprint

def main():
    console = Console()
    base_url = "http://127.0.0.1:8000"

    # Красивый заголовок
    console.print(Panel.fit(
        "[bold cyan]NetData API Client[/bold cyan]\n"
        "[white]Инструмент для проверки геокодирования[/white]",
        border_style="cyan"
    ))

    # Ручной ввод токена
    rprint("[yellow]Совет:[/yellow] Токен можно найти в письме после регистрации в системе.")
    token = Prompt.ask("[bold green]Введите ваш API токен[/bold green]")

    if not token:
        console.print("[red]Ошибка: Токен не может быть пустым![/red]")
        return

    console.print(f"\n[bold]Подключение к:[/bold] [underline]{base_url}[/underline]\n")
    console.print("[blue]Подсказка: Для теста попробуйте ввести:[/blue] [bold white]Часовая 10[/bold white]")

    while True:
        user_query = Prompt.ask("\n[bold]Введите адрес для поиска[/bold] (или [red]'exit'[/red])")
        
        if user_query.lower() in ['exit', 'quit', 'выход']:
            console.print("[yellow]Завершение работы клиента...[/yellow]")
            break

        payload = {"address_query": user_query}
        headers = {
            "X-Token": token,
            "Content-Type": "application/json"
        }

        with console.status("[bold green]Запрос к API...") as status:
            try:
                response = requests.post(
                    f"{base_url}/search", 
                    json=payload, 
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Красивый вывод результата
                    console.print("\n[bold green]✅ Ответ получен:[/bold green]")
                    
                    # Если API вернул данные здания
                    if isinstance(result, dict) and "full_address" in result:
                        table = Table(title="Результат поиска", show_header=True, header_style="bold magenta")
                        table.add_column("Поле", style="dim")
                        table.add_column("Значение")
                        
                        table.add_row("Адрес", result.get("full_address"))
                        table.add_row("Координаты", f"{result.get('latitude')}, {result.get('longitude')}")
                        table.add_row("Год постройки", str(result.get("build_year")))
                        table.add_row("Район", result.get("district"))
                        table.add_row("UNOM", result.get("unom_id"))
                        
                        console.print(table)
                    else:
                        # Если формат ответа другой, просто печатаем JSON
                        console.print_json(data=result)
                
                elif response.status_code == 403:
                    console.print(f"[bold red]❌ Ошибка 403:[/bold red] {response.json().get('detail', 'Доступ запрещен')}")
                else:
                    console.print(f"[bold red]❌ Ошибка {response.status_code}:[/bold red] {response.text}")

            except requests.exceptions.ConnectionError:
                console.print("[bold red]❌ Ошибка:[/bold red] Не удалось подключиться к серверу. Убедитесь, что [blue]main.py[/blue] запущен.")
            except Exception as e:
                console.print(f"[bold red]❌ Непредвиденная ошибка:[/bold red] {e}")

if __name__ == "__main__":
    main()