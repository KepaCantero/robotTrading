"""
AuditTrail - Auditoría completa y reproducibilidad de backtests.

Permite:
- Generar hash único por configuración y versión
- Registrar metadatos de ejecución
- Verificar reproducibilidad
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

# REQUIRED: aiofiles is REQUIRED - NO FALLBACKS
import aiofiles

logger = logging.getLogger(__name__)


class AuditTrail:
    """
    Sistema de auditoría para garantizar reproducibilidad de backtests.

    Genera hashes únicos por configuración, versión de código y commit,
    permitiendo reproducir exactamente cualquier ejecución pasada.
    """

    def __init__(self, log_file: str = "logs/audit_log.jsonl", enable_git_tracking: bool = True):
        """
        Inicializar sistema de auditoría.

        Args:
            log_file: Ruta al archivo de log (formato JSONL)
            enable_git_tracking: Habilitar tracking de Git (commit ID, etc.)
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.enable_git_tracking = enable_git_tracking

        logger.info(f"AuditTrail inicializado: log_file={log_file}")

    def generate_hash(
        self,
        config_path: str,
        code_version: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> str:
        """
        Generar hash SHA256 único para una configuración.

        Args:
            config_path: Ruta al archivo YAML de configuración
            code_version: Versión del código (default: git commit si disponible)
            additional_data: Datos adicionales a incluir en hash

        Returns:
            Hash SHA256 hexadecimal
        """
        logger.debug(f"Generando hash para {config_path}...")

        # Leer configuración
        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_path}")

        with open(config_path_obj, "rb") as f:
            config_content = f.read()

        # Obtener versión de código
        if code_version is None:
            code_version = self._get_code_version()

        # Obtener información adicional
        git_info = self._get_git_info() if self.enable_git_tracking else {}

        # Construir string para hash
        hash_input: dict[str, Any] = {
            "config_content": config_content.decode("utf-8"),
            "code_version": code_version,
            "git_commit": git_info.get("commit_hash", ""),
            "git_branch": git_info.get("branch", ""),
            "timestamp": datetime.now().isoformat(),
        }

        if additional_data:
            hash_input["additional"] = additional_data

        # Convertir a string determinístico
        hash_string = json.dumps(hash_input, sort_keys=True, ensure_ascii=False)

        # Generar hash
        hash_obj = hashlib.sha256(hash_string.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()

        logger.debug(f"Hash generado: {hash_hex[:16]}...")

        return hash_hex

    def _get_code_version(self) -> str:
        """Obtener versión del código."""
        # Intentar obtener de Git
        if self.enable_git_tracking:
            git_info = self._get_git_info()
            commit_hash = git_info.get("commit_hash")
            if commit_hash:
                return str(commit_hash)

        # Fallback: timestamp
        return datetime.now().strftime("%Y%m%d")

    def _get_git_info(self) -> dict[str, Any]:
        """Obtener información de Git."""
        git_info: dict[str, Any] = {"commit_hash": "", "branch": "", "is_dirty": False}

        try:
            # Commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5
            )
            git_info["commit_hash"] = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Error getting git commit hash: {e}", exc_info=True)

        try:
            # Branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-re", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            git_info["branch"] = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Error getting git branch: {e}", exc_info=True)

        try:
            # Check si hay cambios sin commit
            diff_result = subprocess.run(
                ["git", "diff", "--quiet"], capture_output=True, check=False, timeout=5
            )
            git_info["is_dirty"] = diff_result.returncode != 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            git_info["is_dirty"] = True  # Asumir dirty si no se puede verificar
            logger.debug(f"Error checking git dirty state: {e}", exc_info=True)

        return git_info

    async def save_audit_record(
        self,
        config_path: str,
        hash_value: str,
        metadata: dict[str, Any] | None = None,
        result_path: str | None = None,
    ) -> None:
        """
        Guardar registro de auditoría (asíncrono).

        Args:
            config_path: Ruta al archivo de configuración
            hash_value: Hash generado para esta ejecución
            metadata: Metadatos adicionales
            result_path: Ruta a resultados de backtest
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "config_path": str(config_path),
            "hash": hash_value,
            "code_version": self._get_code_version(),
            "git_info": self._get_git_info() if self.enable_git_tracking else {},
            "metadata": metadata or {},
            "result_path": str(result_path) if result_path else None,
        }

        # Guardar en JSONL (una línea por registro)
        async with aiofiles.open(self.log_file, "a") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(f"✅ Registro de auditoría guardado: {hash_value[:16]}...")

    def save_audit_record_sync(
        self,
        config_path: str,
        hash_value: str,
        metadata: dict[str, Any] | None = None,
        result_path: str | None = None,
    ) -> None:
        """
        Guardar registro de auditoría (síncrono).

        Args:
            config_path: Ruta al archivo de configuración
            hash_value: Hash generado para esta ejecución
            metadata: Metadatos adicionales
            result_path: Ruta a resultados de backtest
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "config_path": str(config_path),
            "hash": hash_value,
            "code_version": self._get_code_version(),
            "git_info": self._get_git_info() if self.enable_git_tracking else {},
            "metadata": metadata or {},
            "result_path": str(result_path) if result_path else None,
        }

        # Guardar en JSONL (una línea por registro)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(f"✅ Registro de auditoría guardado: {hash_value[:16]}...")

    def verify_reproducibility(self, target_hash: str) -> dict[str, Any]:
        """
        Verificar si una configuración puede reproducirse.

        Args:
            target_hash: Hash de la ejecución a reproducir

        Returns:
            Dict con información de reproducibilidad
        """
        logger.info(f"🔍 Verificando reproducibilidad para hash {target_hash[:16]}...")

        # Buscar registro con ese hash
        record = self._find_record_by_hash(target_hash)

        if not record:
            return {
                "reproducible": False,
                "reason": "Hash no encontrado en registros de auditoría",
                "target_hash": target_hash,
            }

        # Verificar si el código actual coincide
        current_code_version = self._get_code_version()
        record_code_version = record.get("code_version", "")

        code_matches = current_code_version == record_code_version

        # Verificar si la configuración existe
        config_path = Path(record.get("config_path", ""))
        config_exists = config_path.exists()

        # Verificar si es un commit limpio
        git_info = self._get_git_info() if self.enable_git_tracking else {}
        is_dirty = git_info.get("is_dirty", False)

        reproducible = code_matches and config_exists and not is_dirty

        result = {
            "reproducible": reproducible,
            "target_hash": target_hash,
            "record_found": True,
            "code_version_matches": code_matches,
            "current_code_version": current_code_version,
            "record_code_version": record_code_version,
            "config_exists": config_exists,
            "config_path": str(config_path),
            "is_dirty": is_dirty,
            "original_timestamp": record.get("timestamp"),
            "metadata": record.get("metadata", {}),
        }

        if reproducible:
            logger.info("✅ La ejecución es reproducible")
        else:
            logger.warning("⚠️ La ejecución NO es reproducible")
            if not code_matches:
                logger.warning(
                    f"   Versión de código no coincide: {current_code_version} vs {record_code_version}"
                )
            if not config_exists:
                logger.warning(f"   Configuración no encontrada: {config_path}")
            if is_dirty:
                logger.warning("   Hay cambios sin commit en el código")

        return result

    def _find_record_by_hash(self, target_hash: str) -> dict[str, Any] | None:
        """Buscar registro por hash."""
        if not self.log_file.exists():
            return None

        with open(self.log_file) as f:
            for line in f:
                try:
                    record: dict[str, Any] = json.loads(line.strip())
                    if record.get("hash") == target_hash:
                        return record
                except json.JSONDecodeError:
                    continue

        return None

    def list_audit_records(
        self, limit: int | None = None, filter_by_config: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Listar registros de auditoría.

        Args:
            limit: Número máximo de registros (None = todos)
            filter_by_config: Filtrar por ruta de configuración

        Returns:
            Lista de registros
        """
        if not self.log_file.exists():
            return []

        records = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    record = json.loads(line.strip())

                    # Filtrar por configuración si se especifica
                    if filter_by_config and filter_by_config not in record.get("config_path", ""):
                        continue

                    records.append(record)

                    # Limitar número de registros
                    if limit and len(records) >= limit:
                        break

                except json.JSONDecodeError:
                    continue

        # Ordenar por timestamp (más reciente primero)
        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return records
