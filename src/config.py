"""Configuration management for the application."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "garmin_connect"
    user: str = "garmin"
    password: str = ""
    pool_min_size: int = 1
    pool_max_size: int = 10


@dataclass
class GarminConfig:
    """Garmin Connect configuration."""
    tokens_dir: Path = field(default_factory=lambda: Path.home() / ".garminconnect")
    email: Optional[str] = None
    password: Optional[str] = None
    token_key: Optional[str] = None  # Fernet key for encrypting/decrypting DB tokens


@dataclass
class SyncConfig:
    """Synchronization configuration."""
    categories: List[str] = field(default_factory=lambda: [
        "daily_health",
        "activities",
        "body_composition",
        "advanced_metrics",
        "wellness",
    ])
    mode: str = "incremental"  # incremental or full
    days_back: int = 90  # For full sync
    rate_limit_delay: float = 0.5  # Seconds between API calls


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    log_to_console: bool = True
    log_to_file: bool = True


@dataclass
class Config:
    """Main application configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    garmin: GarminConfig = field(default_factory=GarminConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Config instance
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data or {})

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance
        """
        # Database config
        db_data = data.get("database", {})
        database = DatabaseConfig(
            host=cls._get_env_or_key(db_data, "host", "POSTGRES_HOST", "localhost"),
            port=int(cls._get_env_or_key(db_data, "port", "POSTGRES_PORT", 5432)),
            database=cls._get_env_or_key(db_data, "database", "POSTGRES_DB", "garmin_connect"),
            user=cls._get_env_or_key(db_data, "user", "POSTGRES_USER", "garmin"),
            password=cls._get_env_or_key(db_data, "password", "POSTGRES_PASSWORD", ""),
            pool_min_size=db_data.get("pool_min_size", 1),
            pool_max_size=db_data.get("pool_max_size", 10),
        )

        # Garmin config
        garmin_data = data.get("garmin", {})
        tokens_dir_str = cls._get_env_or_key(
            garmin_data,
            "tokens_dir",
            "GARMIN_TOKENS_DIR",
            str(Path.home() / ".garminconnect")
        )
        garmin = GarminConfig(
            tokens_dir=Path(tokens_dir_str).expanduser(),
            email=cls._get_env_or_key(garmin_data, "email", "GARMIN_EMAIL", None),
            password=cls._get_env_or_key(garmin_data, "password", "GARMIN_PASSWORD", None),
            token_key=cls._get_env_or_key(garmin_data, "token_key", "GARMIN_TOKEN_KEY", None),
        )

        # Sync config
        sync_data = data.get("sync", {})
        sync = SyncConfig(
            categories=sync_data.get("categories", SyncConfig().categories),
            mode=sync_data.get("mode", "incremental"),
            days_back=sync_data.get("days_back", 90),
            rate_limit_delay=sync_data.get("rate_limit_delay", 0.5),
        )

        # Logging config
        log_data = data.get("logging", {})
        logging = LoggingConfig(
            level=os.getenv("LOG_LEVEL", log_data.get("level", "INFO")),
            log_dir=Path(log_data.get("log_dir", "logs")),
            log_to_console=log_data.get("log_to_console", True),
            log_to_file=log_data.get("log_to_file", True),
        )

        return cls(
            database=database,
            garmin=garmin,
            sync=sync,
            logging=logging,
        )

    @staticmethod
    def _get_env_or_key(
        data: Dict[str, Any],
        key: str,
        env_var: str,
        default: Any = None
    ) -> Any:
        """Get value from environment variable or dict key.

        Priority: Environment variable > Dict key > Default

        Args:
            data: Dictionary to check
            key: Key in dictionary
            env_var: Environment variable name
            default: Default value

        Returns:
            Value from env var, dict, or default
        """
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value
        return data.get(key, default)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables only.

        Returns:
            Config instance
        """
        return cls.from_dict({})

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate database config
        if not self.database.password:
            raise ValueError("Database password is required")

        # Validate Garmin tokens directory
        if not self.garmin.tokens_dir.exists():
            raise ValueError(
                f"Garmin tokens directory does not exist: {self.garmin.tokens_dir}"
            )

        # Validate sync mode
        if self.sync.mode not in ("incremental", "full"):
            raise ValueError(f"Invalid sync mode: {self.sync.mode}")

        # Validate categories
        valid_categories = {
            "daily_health",
            "activities",
            "body_composition",
            "advanced_metrics",
            "wellness",
        }
        for cat in self.sync.categories:
            if cat not in valid_categories:
                raise ValueError(f"Invalid sync category: {cat}")

        # Validate logging level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.logging.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.logging.level}")
