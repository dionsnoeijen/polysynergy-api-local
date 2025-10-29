#!/usr/bin/env python3
"""
JSON Truncate Tool
Recursively truncates long text strings in JSON for easier debugging.

Usage:
    python truncate_json.py <input.json>
    cat input.json | python truncate_json.py
    python truncate_json.py input.json > output.json
"""

import json
import sys
from typing import Any

MAX_LENGTH = 50  # Maximum string length before truncation


def truncate_value(value: Any) -> Any:
    """
    Recursively truncate strings in any data structure.

    Args:
        value: Any JSON-serializable value (string, dict, list, etc.)

    Returns:
        The same structure with truncated strings
    """
    if isinstance(value, str):
        if len(value) > MAX_LENGTH:
            truncated = value[:MAX_LENGTH]
            original_len = len(value)
            return f"{truncated}... [TRUNCATED from {original_len} chars]"
        return value

    elif isinstance(value, dict):
        return {key: truncate_value(val) for key, val in value.items()}

    elif isinstance(value, list):
        return [truncate_value(item) for item in value]

    else:
        # Return as-is for booleans, numbers, None, etc.
        return value


def main():
    """Main entry point for the CLI tool."""
    try:
        # Read JSON from file or stdin
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # Read from stdin
            data = json.load(sys.stdin)

        # Truncate all strings recursively
        truncated_data = truncate_value(data)

        # Output pretty-printed JSON
        print(json.dumps(truncated_data, indent=2, ensure_ascii=False))

    except FileNotFoundError:
        print(f"Error: File '{sys.argv[1]}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
