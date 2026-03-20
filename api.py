import fastapi
import uvicorn
import sys
import os
import time
import smtplib
import secrets
import re
import json
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel
from fastapi import BackgroundTasks
from loguru import logger
from db import Database


class RegistrationRequest(BaseModel):
    login: str
    password: str
    email: str


class API():
    def __init__(self, db: Database, config_path: str = "config.json"):
        self.db = db
        self.config = self._load_config(config_path)
        
        api_config = self.config.get("API", {})
        self.app = fastapi.FastAPI(
            title=api_config.get("title", "NetData API"),
            version=api_config.get("version", "1.0.0")
        )
        
        self.smtp_config = api_config.get("SMTP", {})
        
        self._setup_routes()
        logger.info("API initialized successfully")

    def _load_config(self, config_path: str) -> dict:
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.error(f"Config file not found: {config_path}")
                return {}
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Config loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _setup_routes(self):
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "message": "API is running"
            }
        
        @self.app.get("/info")
        async def get_info():
            return {
                "name": "NetData API",
                "version": "1.0.0",
                "description": "Simple NetData API example"
            }
        
        @self.app.post("/data")
        async def receive_data(data: dict):
            logger.info(f"Received data: {data}")
            return {
                "status": "received",
                "data": data
            }

        @self.app.post("/register")
        async def register(request: RegistrationRequest, background_tasks: BackgroundTasks):
            
            # Валидация данных
            logger.debug(f"Starting registration validation for {request.login}, email: {request.email}, password length: {len(request.password) if request.password else 'None'}")

            validation_errors = self._validate_registration(request)
            
            if validation_errors:
                logger.warning(f"Registration validation failed for {request.login}: {validation_errors}")
                return {
                    "status": "error",
                    "message": "Введены некорректные данные",
                    "errors": validation_errors
                }
            
            logger.debug(f"Registration validation passed for {request.login}")
         
            try:
                cur = self.db.execute("SELECT id FROM users WHERE login = ?", (request.login,))
                if cur.fetchone():
                    logger.warning(f"Login already exists: {request.login}")
                    return {
                        "status": "error",
                        "message": "Введены некорректные данные",
                        "errors": ["Этот логин уже зарегистрирован. Выберите другой логин"]
                    }
            except Exception as e:
                logger.error(f"Database error checking login: {e}")
                return {"status": "error", "message": "Ошибка базы данных"}
            
            logger.debug(f"Token generation starting for {request.login}")
            # Создание токена
            token = secrets.token_urlsafe(32)
            
            try:
                # Добавление пользователя в БД
                logger.debug(f"Adding user to database: {request.login}")
                with self.db.conn:
                    cur = self.db.execute(
                        "INSERT INTO users (login, password) VALUES (?, ?)",
                        (request.login, request.password)
                    )
                    user_id = cur.lastrowid
                    
                    # Добавление токена
                    self.db.execute(
                        "INSERT INTO token (user_id, token_tag) VALUES (?, ?)",
                        (user_id, token)
                    )
                
                logger.info(f"New user registered: {request.login} (ID: {user_id})")
                
                logger.debug(f"Sending token email to {request.email} for user {request.login}")
                # Отправка письма в фоне (не блокирует ответ)
                background_tasks.add_task(
                    self._send_token_email,
                    request.email,
                    request.login,
                    token
                )
                
                return {
                    "status": "success",
                    "message": "Ваш токен для работы с API выслан на указанную при регистрации почту"
                }
            
            except Exception as e:
                logger.error(f"Registration error: {e}")
                return {"status": "error", "message": "Ошибка при регистрации"}

    def _validate_registration(self, request: RegistrationRequest) -> list:
        errors = []
        
        # Валидация логина
        if not request.login or len(request.login) < 3:
            errors.append("Логин должен содержать минимум 3 символа")
        if len(request.login) > 25:
            errors.append("Логин не должен превышать 25 символов")
        if not re.match(r"^[a-zA-Z0-9_-]+$", request.login):
            errors.append("Логин может содержать только латинские буквы, цифры, дефис и подчеркивание")
        
        # Валидация пароля
        if not request.password or len(request.password) < 8:
            errors.append("Пароль должен содержать минимум 8 символов")
        if len(request.password) > 24:
            errors.append("Пароль не должен превышать 24 символов")
        if not re.search(r"[A-Z]", request.password):
            errors.append("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", request.password):
            errors.append("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"[0-9]", request.password):
            errors.append("Пароль должен содержать хотя бы одну цифру")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:',.<>?]", request.password):
            errors.append("Пароль должен содержать хотя бы один спецсимвол (!@#$%^&* и т.д.)")
        
        # Валидация email
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not request.email or not re.match(email_regex, request.email):
            errors.append("Введён некорректный адрес электронной почты")
        
        return errors

    def _send_token_email(self, recipient_email: str, login: str, token: str):
        """Отправка токена на почту (фоновая задача)"""
        try:
            # Составление письма
            subject = "Ваш токен API NetData"
            body = f"""
Привет, {login}!

Спасибо за регистрацию в NetData API.

Ваш токен для доступа:
{token}

Используйте этот токен для всех запросов к API.

---
NetData API
            """
            
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["sender_email"]
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            # Отправка письма
            with smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"]) as server:
                server.starttls()
                server.login(self.smtp_config["sender_email"], self.smtp_config["sender_password"])
                server.send_message(msg)
            
            logger.info(f"Token email sent to {recipient_email} for user {login}")
        
        except Exception as e:
            logger.error(f"Failed to send token email to {recipient_email}: {e}")

        
        

    def run(self):
        try:
            api_config = self.config.get("API", {})
            main_config = self.config.get("MAIN", {})
            
            host = api_config.get("host", "127.0.0.1")
            port = api_config.get("port", 8000)
            log_level = main_config.get("log_level", "info")
            
            logger.info(f"Starting API server on http://{host}:{port}")
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level=log_level
            )

        except Exception as e:
            logger.exception(f"API run aborted, class return exitkey 1, exeption log: {e}")
            return 1
        return 0
    
