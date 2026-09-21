{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "homeassistant": {
      "type": "local",
      "command": ["uvx", "ha-mcp@latest"],
      "enabled": true,
      "environment": {
        "HOMEASSISTANT_URL": "http://homeassistant:8123",
        "HOMEASSISTANT_TOKEN": "op://Dev - Home Lab/Home Assistant/bonaventure hassai token"
      }
    }
  }
}
