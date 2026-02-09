#!/bin/bash
# Watch ralph logs in real-time

echo "=== Ralph Logs Monitor ==="
echo ""
echo "1. Scratchpad (últimas 20 líneas):"
echo "-----------------------------------"
tail -20 .ralph/agent/scratchpad.md
echo ""
echo "2. Monitoreo en tiempo real (Ctrl+C para salir):"
echo "-----------------------------------"
echo "Ejecuta: tail -f .ralph/agent/scratchpad.md"
echo ""
echo "3. Sesiones grabadas:"
echo "-----------------------------------"
ls -la .ralph/logs/session_*.jsonl 2>/dev/null || echo "No hay sesiones grabadas"
echo ""
echo "4. Checkpoints:"
echo "-----------------------------------"
ls -la .ralph/checkpoints/*.json
