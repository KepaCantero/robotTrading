#!/usr/bin/env python3
"""
Ralph Event Emitter

Usage:
    python .ralph/scripts/emit.py <event_name> <json_data>

Example:
    python .ralph/scripts/emit.py "task.complete" '{"task_id": "01_protocol_interfaces"}'
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any


def emit(event: str, data: dict[str, Any]) -> None:
    """
    Emite evento al sistema Ralph

    Args:
        event: Nombre del evento (ej: "task.complete", "task.failed")
        data: Datos del evento (serializable a JSON)
    """
    # Crear directorio de eventos si no existe
    events_dir = Path(".ralph/events")
    events_dir.mkdir(parents=True, exist_ok=True)

    # Archivo de log para este evento
    event_file = events_dir / f"{event}.log"

    # Crear entrada de evento
    log_entry = {
        "event": event,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # Añadir al log (append-only)
    with open(event_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # También imprimir a stdout para debugging
    print(f"[EMIT] {event}: {json.dumps(data, indent=2)}")


def main() -> int:
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python emit.py <event_name> <json_data>", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print('  python emit.py "task.complete" \'{"task_id": "01"}\'', file=sys.stderr)
        print('  python emit.py "task.next" \'{"phase": 2}\'', file=sys.stderr)
        return 1

    event = sys.argv[1]

    # Parse data si se proporcionó
    data = {}
    if len(sys.argv) > 2:
        try:
            data = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON data: {e}", file=sys.stderr)
            return 1

    # Emitir evento
    emit(event, data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
