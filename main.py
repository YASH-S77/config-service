
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce(key, value):
    key = key.lower()

    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return str(value).strip().lower() in ("true", "1", "yes", "on")

    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    env_name = os.getenv("APP_ENV", "development")
    yaml_file = BASE_DIR / f"config.{env_name}.yaml"

    if yaml_file.exists():
        with yaml_file.open("r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            config[key.lower()] = coerce(key, value)

    # Layer 3: .env file
    env_file = dotenv_values(BASE_DIR / ".env")

    for key, value in env_file.items():
        if value is None:
            continue

        key_lower = key.lower()

        if key_lower == "num_workers":
            key_lower = "workers"
        elif key_lower.startswith("app_"):
            key_lower = key_lower[4:]

        config[key_lower] = coerce(key_lower, value)

    # Layer 4: OS environment variables (APP_* only)
    for key, value in os.environ.items():
        if key.upper().startswith("APP_"):
            config_key = key[4:].lower()
            config[config_key] = coerce(config_key, value)

    # Layer 5: CLI/query overrides
    for item in set or []:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        config[key.strip().lower()] = coerce(key.strip(), value)

    # Never expose the actual API key
    config["api_key"] = "****"

    return config
