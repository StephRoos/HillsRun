"""Tests for Config management."""

import pytest
import os
import tempfile
from pathlib import Path

from src.config import Config, DatabaseConfig, GarminConfig, SyncConfig, LoggingConfig


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_default_values(self):
        """Test default database configuration values."""
        db_config = DatabaseConfig()
        assert db_config.host == "localhost"
        assert db_config.port == 5432
        assert db_config.database == "garmin_connect"
        assert db_config.user == "garmin"
        assert db_config.password == ""
        assert db_config.pool_min_size == 1
        assert db_config.pool_max_size == 10

    def test_custom_values(self):
        """Test custom database configuration values."""
        db_config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            database="custom_db",
            user="custom_user",
            password="custom_pass",
            pool_min_size=2,
            pool_max_size=20,
        )
        assert db_config.host == "db.example.com"
        assert db_config.port == 5433
        assert db_config.database == "custom_db"
        assert db_config.user == "custom_user"
        assert db_config.password == "custom_pass"
        assert db_config.pool_min_size == 2
        assert db_config.pool_max_size == 20


class TestGarminConfig:
    """Tests for GarminConfig dataclass."""

    def test_default_values(self, tmp_path):
        """Test default Garmin configuration values."""
        garmin_config = GarminConfig()
        assert garmin_config.email is None
        assert garmin_config.password is None
        assert garmin_config.token_key is None
        # tokens_dir defaults to ~/.garminconnect
        assert isinstance(garmin_config.tokens_dir, Path)

    def test_custom_values(self, tmp_path):
        """Test custom Garmin configuration values."""
        tokens_dir = tmp_path / "tokens"
        tokens_dir.mkdir()
        garmin_config = GarminConfig(
            tokens_dir=tokens_dir,
            email="test@garmin.com",
            password="test_pass",
            token_key="test_key",
        )
        assert garmin_config.email == "test@garmin.com"
        assert garmin_config.password == "test_pass"
        assert garmin_config.token_key == "test_key"
        assert garmin_config.tokens_dir == tokens_dir


class TestSyncConfig:
    """Tests for SyncConfig dataclass."""

    def test_default_values(self):
        """Test default sync configuration values."""
        sync_config = SyncConfig()
        assert sync_config.categories == [
            "daily_health",
            "activities",
            "body_composition",
            "advanced_metrics",
            "wellness",
        ]
        assert sync_config.mode == "incremental"
        assert sync_config.days_back == 90
        assert sync_config.rate_limit_delay == 0.5

    def test_custom_values(self):
        """Test custom sync configuration values."""
        sync_config = SyncConfig(
            categories=["daily_health"],
            mode="full",
            days_back=30,
            rate_limit_delay=1.0,
        )
        assert sync_config.categories == ["daily_health"]
        assert sync_config.mode == "full"
        assert sync_config.days_back == 30
        assert sync_config.rate_limit_delay == 1.0


class TestLoggingConfig:
    """Tests for LoggingConfig dataclass."""

    def test_default_values(self):
        """Test default logging configuration values."""
        log_config = LoggingConfig()
        assert log_config.level == "INFO"
        assert log_config.log_to_console is True
        assert log_config.log_to_file is True
        assert isinstance(log_config.log_dir, Path)

    def test_custom_values(self, tmp_path):
        """Test custom logging configuration values."""
        log_config = LoggingConfig(
            level="DEBUG",
            log_dir=tmp_path,
            log_to_console=False,
            log_to_file=False,
        )
        assert log_config.level == "DEBUG"
        assert log_config.log_dir == tmp_path
        assert log_config.log_to_console is False
        assert log_config.log_to_file is False


class TestConfigFromDict:
    """Tests for Config.from_dict method."""

    @pytest.fixture(autouse=True)
    def _clear_config_env(self, monkeypatch):
        """Isolate from_dict tests from leaking environment variables.

        from_dict gives env vars priority over dict values (see
        test_from_dict_with_env_override). The CI sets POSTGRES_*/LOG_LEVEL,
        which would otherwise mask the dict/default behaviour these tests
        exercise. Clearing them keeps the tests hermetic.
        """
        for var in (
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_SSL",
            "GARMIN_TOKENS_DIR",
            "GARMIN_EMAIL",
            "GARMIN_PASSWORD",
            "GARMIN_TOKEN_KEY",
            "LOG_LEVEL",
        ):
            monkeypatch.delenv(var, raising=False)

    def test_from_dict_empty(self):
        """Test creating Config from empty dict uses defaults."""
        config = Config.from_dict({})
        assert config.database.host == "localhost"
        assert config.garmin.email is None
        assert config.sync.mode == "incremental"
        assert config.logging.level == "INFO"

    def test_from_dict_with_database_values(self):
        """Test creating Config with database values."""
        data = {
            "database": {
                "host": "custom.db",
                "port": 5433,
                "database": "custom_db",
                "user": "custom_user",
                "password": "custom_pass",
            }
        }
        config = Config.from_dict(data)
        assert config.database.host == "custom.db"
        assert config.database.port == 5433
        assert config.database.database == "custom_db"
        assert config.database.user == "custom_user"
        assert config.database.password == "custom_pass"

    def test_from_dict_with_env_override(self, monkeypatch):
        """Test that environment variables override dict values."""
        monkeypatch.setenv("POSTGRES_HOST", "env.db.com")
        data = {
            "database": {
                "host": "dict.db.com",
            }
        }
        config = Config.from_dict(data)
        assert config.database.host == "env.db.com"

    def test_from_dict_with_sync_values(self):
        """Test creating Config with sync values."""
        data = {
            "sync": {
                "categories": ["daily_health", "activities"],
                "mode": "full",
                "days_back": 60,
                "rate_limit_delay": 1.5,
            }
        }
        config = Config.from_dict(data)
        assert config.sync.categories == ["daily_health", "activities"]
        assert config.sync.mode == "full"
        assert config.sync.days_back == 60
        assert config.sync.rate_limit_delay == 1.5

    def test_from_dict_with_logging_values(self):
        """Test creating Config with logging values."""
        data = {
            "logging": {
                "level": "DEBUG",
                "log_to_console": False,
                "log_to_file": True,
            }
        }
        config = Config.from_dict(data)
        assert config.logging.level == "DEBUG"
        assert config.logging.log_to_console is False
        assert config.logging.log_to_file is True


class TestConfigFromEnv:
    """Tests for Config.from_env method."""

    def test_from_env_uses_defaults(self, monkeypatch):
        """Test from_env creates config with environment defaults."""
        # Clear env vars to use defaults
        monkeypatch.delenv("POSTGRES_HOST", raising=False)
        config = Config.from_env()
        assert config.database.host == "localhost"

    def test_from_env_uses_environment_variables(self, monkeypatch):
        """Test from_env uses environment variables."""
        monkeypatch.setenv("POSTGRES_HOST", "env.db")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("POSTGRES_DB", "env_db")
        monkeypatch.setenv("POSTGRES_USER", "env_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "env_pass")
        config = Config.from_env()
        assert config.database.host == "env.db"
        assert config.database.port == 5433
        assert config.database.database == "env_db"
        assert config.database.user == "env_user"
        assert config.database.password == "env_pass"


class TestConfigValidation:
    """Tests for Config.validate method."""

    def test_validate_missing_password(self):
        """Test that missing database password raises ValueError."""
        config = Config(
            database=DatabaseConfig(password=""),
            garmin=GarminConfig(),
            sync=SyncConfig(),
            logging=LoggingConfig(),
        )
        with pytest.raises(ValueError, match="password is required"):
            config.validate()

    def test_validate_missing_tokens_dir(self):
        """Test that missing tokens directory raises ValueError."""
        config = Config(
            database=DatabaseConfig(password="test"),
            garmin=GarminConfig(tokens_dir=Path("/nonexistent")),
            sync=SyncConfig(),
            logging=LoggingConfig(),
        )
        with pytest.raises(ValueError, match="does not exist"):
            config.validate()

    def test_validate_invalid_sync_mode(self, tmp_path):
        """Test that invalid sync mode raises ValueError."""
        config = Config(
            database=DatabaseConfig(password="test"),
            garmin=GarminConfig(tokens_dir=tmp_path),
            sync=SyncConfig(mode="invalid"),
            logging=LoggingConfig(),
        )
        with pytest.raises(ValueError, match="Invalid sync mode"):
            config.validate()

    def test_validate_invalid_category(self, tmp_path):
        """Test that invalid sync category raises ValueError."""
        config = Config(
            database=DatabaseConfig(password="test"),
            garmin=GarminConfig(tokens_dir=tmp_path),
            sync=SyncConfig(categories=["invalid_category"]),
            logging=LoggingConfig(),
        )
        with pytest.raises(ValueError, match="Invalid sync category"):
            config.validate()

    def test_validate_invalid_log_level(self, tmp_path):
        """Test that invalid log level raises ValueError."""
        config = Config(
            database=DatabaseConfig(password="test"),
            garmin=GarminConfig(tokens_dir=tmp_path),
            sync=SyncConfig(),
            logging=LoggingConfig(level="INVALID"),
        )
        with pytest.raises(ValueError, match="Invalid log level"):
            config.validate()

    def test_validate_valid_config(self, tmp_path):
        """Test that valid config passes validation."""
        config = Config(
            database=DatabaseConfig(password="test"),
            garmin=GarminConfig(tokens_dir=tmp_path),
            sync=SyncConfig(),
            logging=LoggingConfig(),
        )
        # Should not raise
        config.validate()
