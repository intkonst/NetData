import fastapi
import uvicorn
import sys
import os
import time
import smtplib
import secrets
import re
import math
import json
from datetime import datetime, timedelta
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

class SearchRequest(BaseModel):
    address_query: str

class LoginRequest(BaseModel):
    login: str
    password: str

class CoordsRequest(BaseModel):
    lat: float
    lon: float
    radius: float = 0.5 


class API():

    def check_token_validity(self, token_from_user: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
        cur = self.db.execute(
            """
            SELECT * FROM token 
            WHERE token_tag = ? 
            AND expires_at > ? 
            AND remaining_requests_counter > 0
            """, 
            (token_from_user, now)
        )
    
        result = cur.fetchone()
        if not result:
            return False, "Токен истек или закончились запросы"
        return True, "OK"
    
    def decrease_token_limit(self, token_from_user: str):
        try:
            with self.db.conn:
                self.db.execute(
                    """
                    UPDATE token 
                    SET remaining_requests_counter = remaining_requests_counter - 1 
                    WHERE token_tag = ? AND remaining_requests_counter > 0
                    """,
                    (token_from_user,)
                )
            logger.debug(f"Counter decreased for token: {token_from_user[:10]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to decrease token counter: {e}")
            return False

    def __init__(self, db: Database, config_path: str = "config.json"):
        self.db = db
        self.config = self._load_config(config_path)
        
        api_config = self.config.get("API", {})
        self.app = fastapi.FastAPI(
            title=api_config.get("title", "NetData API"),
            version=api_config.get("version", "1.0.0")
        )
        
        self.smtp_config = api_config.get("SMTP", {})
        self.token_config = api_config.get("TOKEN", {})
        
        
        self._setup_routes()
        logger.info("API initialized successfully")

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        R = 6371 
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(d_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

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
        async def receive_data(data: dict, request: fastapi.Request):
           
            token = request.headers.get("X-Token")
            if not token:
                return {"status": "error", "message": "Missing token"}

           
            is_valid, msg = self.check_token_validity(token)
            if not is_valid:
                return {"status": "error", "message": msg}

           
            self.decrease_token_limit(token)

            logger.info(f"Received data: {data}")
            return {
                "status": "received",
                "data": data
            }

        
        @self.app.post("/register")
        async def register(request: RegistrationRequest, background_tasks: BackgroundTasks):
            logger.debug(f"Starting registration validation for {request.login}, email: {request.email}")

            validation_errors = self._validate_registration(request)
            if validation_errors:
                return {
                    "status": "error",
                    "message": "Введены некорректные данные",
                    "errors": validation_errors
                }
            
            try:
              
                cur = self.db.execute("SELECT id, verified FROM users WHERE login = ? OR email = ?", 
                                     (request.login, request.email))
                existing_user = cur.fetchone()

                if existing_user:
                   
                    if existing_user['verified'] == 1:
                        return {
                            "status": "error",
                            "message": "Ошибка регистрации",
                            "errors": ["Пользователь с таким логином или почтой уже существует и подтвержден."]
                        }
                    
                  
                    new_token = secrets.token_urlsafe(32)
                    with self.db.conn:
                        self.db.execute(
                            "UPDATE users SET verification_token = ? WHERE id = ?",
                            (new_token, existing_user['id'])
                        )
                    
                    background_tasks.add_task(
                        self._send_verification_email,
                        request.email, request.login, new_token
                    )
                    
                    logger.info(f"Re-sending verification to unverified user: {request.login}")
                    return {
                        "status": "success",
                        "message": "Аккаунт уже ожидает подтверждения. Мы отправили письмо с ссылкой повторно."
                    }

              
                verification_token = secrets.token_urlsafe(32)
                with self.db.conn:
                    self.db.execute(
                        "INSERT INTO users (login, password, email, verified, verification_token) VALUES (?, ?, ?, ?, ?)",
                        (request.login, request.password, request.email, 0, verification_token)
                    )
                
                background_tasks.add_task(
                    self._send_verification_email,
                    request.email, request.login, verification_token
                )
                
                return {
                    "status": "success",
                    "message": "Аккаунт успешно создан. На почту отправлена ссылка для подтверждения."
                }
            
            except Exception as e:
                logger.error(f"Registration error: {e}")
                return {"status": "error", "message": "Ошибка при регистрации"}
            
        
        @self.app.get("/verify")
        async def verify_account(token: str):
            try:
                
                cur = self.db.execute("SELECT id, login FROM users WHERE verification_token = ?", (token,))
                user = cur.fetchone()
                
                if not user:
                    return {"status": "error", "message": "Неверная или устаревшая ссылка подтверждения."}
                
               
                with self.db.conn:
                    self.db.execute(
                        "UPDATE users SET verified = 1, verification_token = NULL WHERE id = ?",
                        (user['id'],)
                    )
                
                logger.info(f"User {user['login']} successfully verified email.")
                return {
                    "status": "success",
                    "message": f"Поздравляем, {user['login']}! Ваш аккаунт успешно подтвержден. Теперь вы можете войти (login)."
                }
            except Exception as e:
                logger.error(f"Verification error: {e}")
                return {"status": "error", "message": "Ошибка при подтверждении аккаунта"}

    
        @self.app.post("/login")
        async def login(request: LoginRequest, background_tasks: BackgroundTasks):
            try:
                
                cur = self.db.execute("SELECT id, email, verified FROM users WHERE login = ? AND password = ?", 
                                      (request.login, request.password))
                user = cur.fetchone()
                
                if not user:
                    return {"status": "error", "message": "Неверный логин или пароль."}
                
                if user['verified'] == 0:
                    return {"status": "error", "message": "Пожалуйста, подтвердите вашу электронную почту перед входом."}
                
               
                api_token = secrets.token_urlsafe(32)
                
                
                requests_limit = self.token_config["requestlimit"]
                time_limit_days = self.token_config["timelimit"]

                # Исправлено: теперь используем time_limit_days вместо 30
                expiration_date = datetime.now() + timedelta(days=time_limit_days) 
                expires_at_str = expiration_date.strftime("%Y-%m-%d %H:%M:%S")

                with self.db.conn:
                    self.db.execute(
                        "INSERT INTO token (user_id, token_tag, remaining_requests_counter, expires_at) VALUES (?, ?, ?, ?)",
                        (user['id'], api_token, requests_limit, expires_at_str)
                    )

                # Теперь данные в базе и в письме будут синхронны
                background_tasks.add_task(
                    self._send_api_token_email,
                    user['email'],
                    request.login,
                    api_token,
                    requests_limit,
                    time_limit_days
                )
                
                return {
                    "status": "success",
                    "message": "Вход выполнен успешно! Данные токена и детали тарифа высланы на вашу почту."
                }

            except Exception as e:
                logger.error(f"Login error: {e}")
                return {"status": "error", "message": "Ошибка при авторизации"}

        @self.app.post("/search")
        async def search_by_address(request_data: SearchRequest, request: fastapi.Request):
         
            token = request.headers.get("X-Token")
            if not token:
                return {"status": "error", "message": "Missing token"}

            is_valid, msg = self.check_token_validity(token)
            if not is_valid:
                return {"status": "error", "message": msg}
            

            logger.debug("Start searching...")

            
            try:
                
                clean_query = re.sub(r'[^\w\s]', ' ', request_data.address_query)
                logger.debug("Correct cleaning")
                
                building_cur = self.db.execute(
                    """
                    SELECT b.* FROM buildings b
                    JOIN buildings_fts fts ON b.rowid = fts.rowid
                    WHERE buildings_fts MATCH ? LIMIT 1
                    """,
                    (clean_query,)
                )

                logger.debug("Correct execute")
                building = building_cur.fetchone()

                if not building:
                    return {
                        "status": "error", 
                        "message": "Адрес не найден",
                        "query": request_data.address_query
                    }

                logger.debug("correct address searching, next step")
              
                building_info = dict(building)
                full_addr = building_info['full_address']

              

                logger.debug("Try search organizations")



                safe_full_addr = full_addr.replace('"', ' ') 
                org_cur = self.db.execute(
                    "SELECT name, address, foundation_date, founder_surname FROM organization WHERE address MATCH ?",
                    (f'"{safe_full_addr}"',)
                )

                organizations = [dict(row) for row in org_cur.fetchall()]
                logger.debug("Succsessful searching")
              
                self.decrease_token_limit(token)

                
                return {
                    "status": "success",
                    "result": {
                        "building": {
                            "full_address": building_info['full_address'],
                            "city": building_info['city'],
                            "district": building_info['district'],
                            "build_year": building_info['build_year'],
                            "coords": {
                                "lat": building_info['latitude'],
                                "lon": building_info['longitude']
                            },
                            "unom": building_info['unom_id']
                        },
                        "organizations_count": len(organizations),
                        "organizations": organizations
                    }
                }

            except Exception as e:
                logger.error(f"Search error: {e}")
                return {"status": "error", "message": "Ошибка при выполнении поиска"}
        


        @self.app.post("/coords")
        async def search_by_coords(request_data: CoordsRequest, request: fastapi.Request):
          
            token = request.headers.get("X-Token")
            if not token:
                return {"status": "error", "message": "Missing token"}

            is_valid, msg = self.check_token_validity(token)
            if not is_valid:
                return {"status": "error", "message": msg}

            logger.debug(f"Start searching near Coords: {request_data.lat}, {request_data.lon}")

            try:
               
                lat_delta = request_data.radius / 111.0
                lon_delta = request_data.radius / (111.0 * abs(math.cos(math.radians(request_data.lat))))

                lat_min, lat_max = request_data.lat - lat_delta, request_data.lat + lat_delta
                lon_min, lon_max = request_data.lon - lon_delta, request_data.lon + lon_delta

                building_cur = self.db.execute(
                    """
                    SELECT * FROM buildings 
                    WHERE latitude BETWEEN ? AND ? 
                    AND longitude BETWEEN ? AND ?
                    """,
                    (lat_min, lat_max, lon_min, lon_max)
                )
                candidates = building_cur.fetchall()

                buildings_dict = {}
                organizations_dict = {}

              
                for b in candidates:
                    b_info = dict(b)
                    
                    dist = self._calculate_distance(
                        request_data.lat, request_data.lon, 
                        b_info['latitude'], b_info['longitude']
                    )

                    if dist <= request_data.radius:
                        addr = b_info['full_address']
                       
                        buildings_dict[addr] = {
                            "dist_km": round(dist, 3),
                            "city": b_info['city'],
                            "build_year": b_info['build_year'],
                            "coords": {"lat": b_info['latitude'], "lon": b_info['longitude']}
                        }

                      
                        org_cur = self.db.execute(
                            "SELECT name, foundation_date, founder_surname FROM organization WHERE address MATCH ?",
                            (f'"{addr}"',)
                        )
                        orgs = [dict(row) for row in org_cur.fetchall()]
                        
                        if orgs:
                            organizations_dict[addr] = orgs

                
                self.decrease_token_limit(token)

                return {
                    "status": "success",
                    "count_found": len(buildings_dict),
                    "result": {
                        "buildings": buildings_dict,
                        "organizations": organizations_dict
                    }
                }

            except Exception as e:
                logger.error(f"Search error by coords: {e}")
                return {"status": "error", "message": f"Ошибка при выполнении поиска: {e}"}
            



    def _validate_registration(self, request: RegistrationRequest) -> list:
        errors = []
        
        if not request.login or len(request.login) < 3:
            errors.append("Логин должен содержать минимум 3 символа")
        if len(request.login) > 25:
            errors.append("Логин не должен превышать 25 символов")
        if not re.match(r"^[a-zA-Z0-9_-]+$", request.login):
            errors.append("Логин может содержать только латинские буквы, цифры, дефис и подчеркивание")
        
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
        
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not request.email or not re.match(email_regex, request.email):
            errors.append("Введён некорректный адрес электронной почты")
        
        return errors

    def _send_verification_email(self, recipient_email: str, login: str, token: str):
        """Отправка ссылки для верификации аккаунта"""
        try:
            api_config = self.config.get("API", {})
            host = api_config.get("host", "127.0.0.1")
            port = api_config.get("port", 8000)
            verify_link = f"http://{host}:{port}/verify?token={token}"

            subject = "Подтверждение регистрации NetData API"
            body = f"""Здравствуйте, {login}!

Вы успешно начали процесс регистрации в NetData API.
Для завершения регистрации и активации аккаунта перейдите по следующей ссылке:

{verify_link}

Если вы не регистрировались на нашем сервисе, просто проигнорируйте это письмо.

С уважением,
Команда NetData API
"""
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["sender_email"]
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            with smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"]) as server:
                server.starttls()
                server.login(self.smtp_config["sender_email"], self.smtp_config["sender_password"])
                server.send_message(msg)
            
            logger.info(f"Verification email sent to {recipient_email} for user {login}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {recipient_email}: {e}")

    def _send_api_token_email(self, recipient_email: str, login: str, token: str, req_limit: int, time_limit: int):
        """Отправка токена доступа и статистики после успешного логина"""
        try:
            subject = "Ваш API Токен | NetData API"
            body = f"""Здравствуйте, {login}!

Вы успешно авторизовались в системе. 
Ваш новый токен для работы с API:

{token}

Информация о вашей подписке:
- Остаток запросов: {req_limit}
- Дней до истечения: {time_limit}

Используйте этот токен для авторизации ваших запросов.

С уважением,
Команда NetData API
"""
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["sender_email"]
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            with smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"]) as server:
                server.starttls()
                server.login(self.smtp_config["sender_email"], self.smtp_config["sender_password"])
                server.send_message(msg)
            
            logger.info(f"API Token email sent to {recipient_email} for user {login}")
        except Exception as e:
            logger.error(f"Failed to send API token email to {recipient_email}: {e}")

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
            logger.exception(f"API run aborted, class return exitkey 1, exception log: {e}")
            return 1
        return 0