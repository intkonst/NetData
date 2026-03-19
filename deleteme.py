# Примеры логирования с разными уровнями
# logger.debug("Это сообщение для отладки (DEBUG)")
# logger.info("Информационное сообщение (INFO)")
# logger.success("Успешное выполнение операции (SUCCESS)")
# logger.warning("Предупреждение (WARNING)")
# logger.error("Произошла ошибка (ERROR)")
# logger.critical("Критическая ошибка (CRITICAL)")
# Пример логирования с переменными
# user = "Alice"
# action = "вход в систему"
# logger.info(f"Пользователь {user} выполнил {action}")
# Логирование исключений
# try:
#     x = 1 / 0
# except Exception as e:
#     logger.exception("Поймано исключение:")