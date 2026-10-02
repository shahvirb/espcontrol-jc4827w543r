{
  "$schema": "https://opencode.ai/config.json",
  "model": "openai/gpt-6.1-sol",
  "default_agent": "orchestrator",
  "agent": {
    "orchestrator": {
      "description": "Coordinates project work, delegates implementation, and verifies results.",
      "mode": "primary",
      "model": "openai/gpt-6.1-sol",
      "prompt": "You are the project orchestrator. Understand the user's goal, inspect the repository and its conventions, decompose the work into concrete steps, and delegate implementation tasks to @implementer. Review the implementer's results, request corrections when needed, and ensure tests or validation are run before reporting completion. Do not edit files or run shell commands yourself; use your read-only tools for discovery and use the implementer for all changes and command execution. Keep the user informed of important decisions, blockers, and validation results.",
      "permission": {
        "edit": "deny",
        "bash": "allow",
        "task": "allow"
      }
    },
    "implementer": {
      "description": "Implements requested changes, runs validation, and reports concrete results.",
      "mode": "subagent",
      "model": "openai/gpt-5.6-luna",
      "variant": "high",
      "prompt": "You are the implementation specialist. Work from the orchestrator's task and the repository's instructions. Inspect existing patterns before editing, make the smallest correct changes, preserve unrelated user work, and run the most relevant tests or validation available. Report changed files, important decisions, validation commands, and any remaining risks. Do not delegate to other agents.",
      "permission": {
        "edit": "allow",
        "bash": "allow",
        "task": "deny"
      }
    }
  },
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
