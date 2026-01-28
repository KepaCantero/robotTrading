# 📘 28. Serious Cryptography - Security y Secrets para Trading

**Libro:** Serious Cryptography - Jean-Philippe Aumasson
**Objetivo:** Seguridad robusta para sistemas de trading

## 🎯 Resumen Ejecutivo

Claude Code DEBE implementar seguridad para:
1. **Proteger** credenciales y API keys
2. **Validar** todas las entradas externas
3. **Audititar** todas las operaciones críticas
4. **Cumplir** estándares de seguridad financiera

---

## 📋 Las 15 Reglas Críticas para Claude Code

### Regla 28.1 — Secret Management (No Hardcoded Secrets)

```python
# ❌ MAL: Secrets en código
API_KEY = "binance_api_key_12345"
SECRET = "my_secret_key"

# ✅ BIEN: Desde variable de entorno
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["BINANCE_API_KEY"]
SECRET = os.environ["BINANCE_API_SECRET"]

if not API_KEY or not SECRET:
    raise ValueError("API credentials not configured")
```

**Regla:** NUNCA hardcoded secrets. Usar variables de entorno.

---

### Regla 28.2 — Environment Variables con Validación

```python
from pydantic import BaseModel, Field

class Settings(BaseModel):
    binance_api_key: str = Field(..., min_length=10)
    binance_api_secret: str = Field(..., min_length=10)
    database_url: str
    redis_url: str
    
    class Config:
        env_file = ".env"

# Uso
settings = Settings()  # Valida al inicio
```

**Regla:** VALIDAR variables de entorno con Pydantic al inicio.

---

### Regla 28.3 — Hashing Seguro (bcrypt/argon2)

```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

**Regla:** USAR bcrypt o argon2 para hashear contraseñas.

---

### Regla 28.4 — JWT Authentication

```python
import jwt
from datetime import datetime, timedelta

def generate_jwt(user_id: str, secret_key: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')

def verify_jwt(token: str, secret_key: str) -> dict:
    try:
        return jwt.decode(token, secret_key, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
```

**Regla:** USAR JWT para autenticación stateless.

---

### Regla 28.5 — HMAC Signing para API Requests

```python
import hmac
import hashlib
import time

def generate_signature(api_secret: str, timestamp: int, method: str, endpoint: str, params: dict) -> str:
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    message = f"{timestamp}{method}{endpoint}{query_string}"
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

# Uso para Binance
timestamp = int(time.time() * 1000)
signature = generate_signature(API_SECRET, timestamp, 'GET', '/api/v3/account', {})
headers = {'X-MBX-APIKEY': API_KEY, 'signature': signature}
```

**Regla:** FIRMAR todas las API requests con HMAC.

---

### Regla 28.6 — TLS/SSL Obligatorio

```python
import aiohttp

async def make_request(url: str):
    # Verificar certificado SSL
    connector = aiohttp.TCPConnector(verify_ssl=True)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as response:
            return await response.json()
```

**Regla:** SIEMPRE usar HTTPS/TLS para comunicaciones de red.

---

### Regla 28.7 — Certificate Pinning

```python
import ssl

ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations('/path/to/cert.pem')

async def make_pinned_request(url: str):
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as response:
            return await response.json()
```

**Regla:** IMPLEMENTAR certificate pinning para APIs críticas.

---

### Regla 28.8 — Rate Limiting

```python
from functools import wraps
import time

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def allow_request(self) -> bool:
        now = time.time()
        self.requests = [t for t in self.requests if t > now - self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

def rate_limit(max_requests: int, time_window: int):
    limiter = RateLimiter(max_requests, time_window)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not limiter.allow_request():
                raise Exception(f"Rate limit exceeded: {max_requests} requests per {time_window}s")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Uso
@rate_limit(max_requests=10, time_window=60)
async def place_order(order: Order):
    pass
```

**Regla:** IMPLEMENTAR rate limiting para todas las APIs externas.

---

### Regla 28.9 — IP Whitelisting

```python
class IPWhitelist:
    def __init__(self, allowed_ips: list[str]):
        self.allowed_ips = set(allowed_ips)
    
    def is_allowed(self, ip: str) -> bool:
        return ip in self.allowed_ips
    
    def check_request(self, request):
        client_ip = request.remote_addr
        if not self.is_allowed(client_ip):
            raise Exception(f"IP {client_ip} not whitelisted")
```

**Regla:** CONFIGURAR IP whitelisting para APIs de brokers.

---

### Regla 28.10 — Zero Trust Architecture

```python
class ZeroTrustValidator:
    def validate_request(self, request):
        # Validar identidad
        if not self.verify_jwt(request.token):
            raise Exception("Invalid identity")
        
        # Validar autorización
        if not self.check_permissions(request.user, request.action):
            raise Exception("Unauthorized")
        
        # Validar contexto
        if self.is_suspicious_location(request.ip):
            raise Exception("Suspicious location")
        
        # Validar dispositivo
        if not self.is_known_device(request.device_id):
            self.require_mfa(request)
```

**Regla:** VALIDAR cada request (zero trust: nunca confiar, siempre verificar).

---

### Regla 28.11 — Audit Logging

```python
import structlog

logger = structlog.get_logger()

class AuditLogger:
    def log_order(self, order: Order, user: str):
        logger.info(
            "order_placed",
            user=user,
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=float(order.quantity),
            price=float(order.price),
            timestamp=datetime.now().isoformat()
        )
    
    def log_trade(self, trade: Trade):
        logger.info(
            "trade_executed",
            order_id=trade.order_id,
            execution_price=float(trade.price),
            execution_quantity=float(trade.quantity),
            commission=float(trade.commission)
        )
```

**Regla:** LOGEAR todas las operaciones críticas para auditoría.

---

### Regla 28.12 — Code Signing

```python
# Firmar commits git
git config commit.gpgsign true
git config user.signingkey YOUR_GPG_KEY_ID

# Commit firmado
git commit -S -m "Add trading strategy"
```

**Regla:** FIRMAR todo el código para verificar autenticidad.

---

### Regla 28.13 — Dependency Scanning

```bash
# pip-audit para vulnerabilities
pip install pip-audit
pip-audit

# Safety check
pip install safety
safety check
```

```python
# requirements.txt con versiones fijas
numpy==1.24.0
pandas==2.0.0
requests==2.28.0
```

**Regla:** ESCANEAR dependencias regularmente por vulnerabilidades.

---

### Regla 28.14 — Secure Random Generation

```python
import secrets
import string

def generate_secure_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_order_id() -> str:
    return secrets.token_hex(16)
```

**Regla:** USAR `secrets` (no `random`) para tokens y IDs criptográficos.

---

### Regla 28.15 — Encryption at Rest

```python
from cryptography.fernet import Fernet

class Encryptor:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())
    
    def decrypt(self, encrypted_data: bytes) -> str:
        return self.cipher.decrypt(encrypted_data).decode()

# Uso
key = Fernet.generate_key()
encryptor = Encryptor(key)

# Guardar API key encriptada
encrypted_api_key = encryptor.encrypt("my_api_key")

# Usar
api_key = encryptor.decrypt(encrypted_api_key)
```

**Regla:** ENCRIPTAR datos sensibles en disco (API keys, secrets).

---

**Última actualización:** 2026-01-28
**Version:** 1.0
