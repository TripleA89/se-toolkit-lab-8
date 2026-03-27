#!/usr/bin/env python3
"""Entrypoint for nanobot gateway in Docker.

Resolves environment variables into config.json at runtime,
then execs 'nanobot gateway'.
"""

import json
import os
import sys
from pathlib import Path


def resolve_config() -> str:
    """Read config.json, inject env vars, write config.resolved.json."""
    config_path = Path(__file__).parent / "config.json"
    resolved_path = Path(__file__).parent / "config.resolved.json"

    with open(config_path) as f:
        config = json.load(f)

    # Resolve LLM provider API key and base URL from env
    # Match docker-compose environment variable names
    if "providers" in config and "custom" in config["providers"]:
        api_key = os.environ.get("LLM_API_KEY", "")
        api_base = os.environ.get("LLM_API_BASE_URL", "")
        if api_key:
            config["providers"]["custom"]["apiKey"] = api_key
        if api_base:
            config["providers"]["custom"]["apiBase"] = api_base

    # Resolve gateway host/port from env
    gateway_host = os.environ.get("NANOBOT_GATEWAY_CONTAINER_ADDRESS", "0.0.0.0")
    gateway_port = os.environ.get("NANOBOT_GATEWAY_CONTAINER_PORT", "18790")
    if "gateway" not in config:
        config["gateway"] = {}
    config["gateway"]["host"] = gateway_host
    config["gateway"]["port"] = int(gateway_port)

    # Resolve webchat host/port from env
    webchat_host = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_ADDRESS", "0.0.0.0")
    webchat_port = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_PORT", "8765")
    if "channels" not in config:
        config["channels"] = {}
    if "webchat" not in config["channels"]:
        config["channels"]["webchat"] = {}
    config["channels"]["webchat"]["host"] = webchat_host
    config["channels"]["webchat"]["port"] = int(webchat_port)

    # Resolve MCP server env vars (LMS backend URL and API key)
    if "tools" in config and "mcpServers" in config["tools"]:
        if "lms" in config["tools"]["mcpServers"]:
            lms_backend_url = os.environ.get("NANOBOT_LMS_BACKEND_URL", "")
            lms_api_key = os.environ.get("NANOBOT_LMS_API_KEY", "")
            if "env" not in config["tools"]["mcpServers"]["lms"]:
                config["tools"]["mcpServers"]["lms"]["env"] = {}
            if lms_backend_url:
                config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_BACKEND_URL"] = lms_backend_url
            if lms_api_key:
                config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_API_KEY"] = lms_api_key

    # Write resolved config
    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)

    return str(resolved_path)


def main() -> None:
    resolved_config = resolve_config()
    workspace = str(Path(__file__).parent / "workspace")

    # Exec nanobot gateway
    os.execvp("nanobot", ["nanobot", "gateway", "--config", resolved_config, "--workspace", workspace])


if __name__ == "__main__":
    sys.exit(main())
