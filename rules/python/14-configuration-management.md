# Configuration Management

Environment-based configuration using Pydantic Settings.

## Table of Contents
1. Environment-based Configuration
2. Settings Validation
3. Secrets Management
4. Feature Flags
5. Dynamic Configuration
6. Configuration File Formats

---

## Environment-based Configuration

### Pydantic Settings

```python
# ✅ CORRECT - Base configuration class
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="forbid",
    )

    # Application
    app_name: str = Field(default="MyApp", description="Application name")
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Server
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # Database
    database_url: str = Field(
        ...,
        description="Database connection string",
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)

    # Security
    secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key for encryption",
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = Field(default=3600, ge=60)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is not default in production."""
        if v == "change-me":
            raise ValueError("secret_key must be set in production")
        return v


# Global settings instance
settings = Settings()
```

### Environment-specific Configuration

```python
# ✅ CORRECT - Environment-aware settings
from enum import Enum

class Environment(str, Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Environment-aware settings."""

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )

    debug: bool = Field(default=True)
    log_level: str = Field(default="DEBUG")
    database_url: str = Field(default="postgresql://localhost/dev")

    @field_validator("debug", "log_level", mode="before")
    @classmethod
    def set_environment_defaults(cls, v: Any, info: FieldValidationInfo) -> Any:
        """Set defaults based on environment."""
        env = info.data.get("environment", Environment.DEVELOPMENT)

        if info.field_name == "debug":
            return env != Environment.PRODUCTION
        if info.field_name == "log_level":
            return "INFO" if env == Environment.PRODUCTION else "DEBUG"
        return v
```

### Environment Files

```bash
# .env.development
APP_ENVIRONMENT=development
APP_DEBUG=true
APP_DATABASE_URL=postgresql://localhost/dev
APP_LOG_LEVEL=DEBUG

# .env.production
APP_ENVIRONMENT=production
APP_DEBUG=false
APP_DATABASE_URL=postgresql://prod-server/app
APP_SECRET_KEY=<production-secret>
APP_LOG_LEVEL=INFO
```

---

## Settings Validation

### URL Validation

```python
# ✅ CORRECT - URL validation
class ApiSettings(BaseSettings):
    """API configuration with URL validation."""

    base_url: str
    timeout: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate URL format."""
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError(f"Invalid URL: {v}")
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https")
        return v.rstrip("/")
```

### Database Settings Validation

```python
# ✅ CORRECT - Database configuration with validation
class DatabaseSettings(BaseSettings):
    """Database configuration with validation."""

    host: str
    port: int = Field(default=5432, ge=1, le=65535)
    username: str
    password: str
    database: str
    pool_size: int = Field(default=10, ge=1, le=100)
    ssl_mode: Literal["disable", "require", "verify-ca", "verify-full"] = "require"

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate hostname."""
        if not v:
            raise ValueError("Database host cannot be empty")
        return v

    @property
    def connection_string(self) -> str:
        """Build connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
```

---

## Secrets Management

### Encrypted Secrets

```python
# ✅ CORRECT - Secrets management
from cryptography.fernet import Fernet
from pathlib import Path

class SecretsManager:
    """Manage encrypted secrets."""

    def __init__(self, key_file: Path) -> None:
        self._key_file = key_file
        self._fernet = self._load_or_create_key()

    def _load_or_create_key(self) -> Fernet:
        """Load or create encryption key."""
        if self._key_file.exists():
            key = self._key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self._key_file.write_bytes(key)
            self._key_file.chmod(0o600)
        return Fernet(key)

    def encrypt(self, value: str) -> bytes:
        """Encrypt secret value."""
        return self._fernet.encrypt(value.encode())

    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt secret value."""
        return self._fernet.decrypt(encrypted).decode()


class SecureSettings(BaseSettings):
    """Settings with encrypted secrets."""

    api_endpoint: str
    timeout: int = 30
    database_password: str = Field(..., min_length=32)

    @field_validator("database_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password is strong."""
        if len(v) < 32:
            raise ValueError("Password too short")
        return v
```

### ❌ INCORRECT - Hardcoded secrets

```python
# ❌ NEVER DO THIS - Secrets in code
class Settings:
    AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
    AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

---

## Feature Flags

```python
# ✅ CORRECT - Feature flags configuration
class FeatureFlags(BaseSettings):
    """Feature flag configuration."""

    # Boolean flags
    enable_new_ui: bool = False
    enable_v2_api: bool = False
    enable_analytics: bool = True

    # Percentage-based flags (0-100)
    rollout_percentage: int = Field(default=0, ge=0, le=100)

    # Whitelist-based flags
    enabled_user_ids: list[int] = Field(default_factory=list)
    enabled_email_domains: list[str] = Field(default_factory=list)

    def is_enabled_for_user(self, user: Any) -> bool:
        """Check if feature is enabled for specific user."""
        # Check whitelist
        if user.id in self.enabled_user_ids:
            return True

        # Check email domain
        user_domain = user.email.split("@")[-1]
        if user_domain in self.enabled_email_domains:
            return True

        # Check percentage rollout
        if self.rollout_percentage > 0:
            hash_value = hash(user.id) % 100
            return hash_value < self.rollout_percentage

        return False


# Usage
flags = FeatureFlags()

if flags.enable_v2_api:
    response = call_v2_api()
else:
    response = call_v1_api()

if flags.is_enabled_for_user(current_user):
    show_new_feature()
```

---

## Dynamic Configuration

### Runtime-reloadable Configuration

```python
# ✅ CORRECT - Runtime-reloadable configuration
import asyncio
from typing import TypeVar, Type
from pathlib import Path

T = TypeVar('T', bound=BaseSettings)


class ConfigWatcher:
    """Watch for configuration changes."""

    def __init__(
        self,
        config_class: Type[T],
        env_file: Path = Path(".env"),
    ) -> None:
        self._config_class = config_class
        self._env_file = env_file
        self._current: T = config_class()
        self._mtime: float = env_file.stat().st_mtime if env_file.exists() else 0

    def get(self) -> T:
        """Get current configuration."""
        return self._current

    async def watch(self, interval: float = 5.0) -> None:
        """Watch for changes."""
        while True:
            await asyncio.sleep(interval)
            await self._check_for_changes()

    async def _check_for_changes(self) -> None:
        """Check and reload if file changed."""
        if not self._env_file.exists():
            return

        current_mtime = self._env_file.stat().st_mtime
        if current_mtime > self._mtime:
            logger.info("Configuration file changed, reloading...")
            self._current = self._config_class()
            self._mtime = current_mtime
            await self._on_config_changed()

    async def _on_config_changed(self) -> None:
        """Called when configuration changes."""
        logger.info(f"New configuration: {self._current.model_dump()}")


# Usage
watcher = ConfigWatcher(Settings)

async def main():
    asyncio.create_task(watcher.watch())

    while True:
        config = watcher.get()
        print(f"Using config: {config.app_name}")
        await asyncio.sleep(10)
```

---

## Configuration File Formats

### Multi-format Support

```python
# ✅ CORRECT - Support multiple formats
import yaml
import toml

class MultiFormatSettings(BaseSettings):
    """Settings supporting multiple formats."""

    app_name: str
    debug: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> "MultiFormatSettings":
        """Load from YAML file."""
        data = yaml.safe_load(path.read_text())
        return cls(**data)

    @classmethod
    def from_toml(cls, path: Path) -> "MultiFormatSettings":
        """Load from TOML file."""
        data = toml.loads(path.read_text())
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        """Save to YAML file."""
        path.write_text(yaml.dump(self.model_dump()))
```

### YAML Configuration

```yaml
# config.yaml
app_name: "MyApp"
debug: true

database:
  url: "postgresql://localhost/mydb"
  pool_size: 10

security:
  secret_key: "production-secret-key-here"
  jwt_expiration: 3600
```

### TOML Configuration

```toml
# config.toml
app_name = "MyApp"
debug = true

[database]
url = "postgresql://localhost/mydb"
pool_size = 10

[security]
secret_key = "production-secret-key-here"
jwt_expiration = 3600
```

---

## Configuration Checklist

- [ ] Use Pydantic Settings for type-safe configuration
- [ ] Never hardcode secrets in code
- [ ] Use environment variables for deployment-specific values
- [ ] Validate all configuration values
- [ ] Provide sensible defaults
- [ ] Document all fields with `description`
- [ ] Use environment-specific configuration files
- [ ] Encrypt secrets at rest
- [ ] Use environment variables for secrets in production
- [ ] Implement feature flags for gradual rollouts
- [ ] Support configuration hot-reload when needed
- [ ] Use environment prefix to avoid conflicts
- [ ] Set `extra="forbid"` to catch typos
- [ ] Add field validators for complex validation
