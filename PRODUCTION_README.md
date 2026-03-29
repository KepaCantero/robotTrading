# Guia de Produccion - algoTrading

## Resumen

Este documento explica los flujos de trabajo disponibles para llevar el codigo de algoTrading a produccion, usando **Ralph**, **OpenHands**, **Aider** y las herramientas de calidad configuradas.

---

## Flujo Recomendado (AAA Production Pipeline)

```bash
ralph -c .ralph/ralph_tasks/34_aaa_production.yml
```

Pipeline completo de 12 hats que integra **Ruff + Aider + OpenHands + Confession Loop** para llevar el codigo a estandar AAA:

1. Discovery -> 2. Aider Formatter -> 3. Deep Linter -> 4. Deep Fixer -> 5. Requirements -> 6. Architecture -> 7. OpenHands -> 8. Anti-Patterns -> 9. Confession Loop -> 10. Aider Fix-up -> 11. Tests -> 12. Final Validation

**7 quality gates automaticos**: ruff lint, ruff format, mypy, bandit, safety, pytest coverage >= 80%, validate_file_complete.sh

**Herramientas integradas**:
- **Ruff**: auto-fix masivo de lint + formato
- **Aider**: fix complejo con AI pair programming (fallback manual)
- **OpenHands**: resolucion de issues arquitecturales via GitHub
- **Confession Loop**: self-audit con 4 perspectivas (Critic, Architect, Engineer, Steward)

---

## Flujo Anterior (aun disponible)

```bash
ralph -c .ralph/ralph_tasks/31_production_audit.yml
```

Pipeline de 10 hats (discovery -> requirements -> audit -> compliance -> architecture -> fix -> anti-patterns -> QA -> tests -> final).

**Sigue funcionando** como alternativa mas simple sin integracion con Aider/OpenHands.

---

## Flujos de Trabajo Disponibles

### 1. Quick Quality Check (manual, rapido)

Ejecuta todas las herramientas de calidad en secuencia:

```bash
make quality
```

Esto ejecuta:
- `ruff check .` (lint)
- `ruff format --check .` (formato)
- `mypy app/` (tipos)
- `bandit -r app/ -ll` (seguridad)
- `safety check` (vulnerabilidades en dependencias)

Para fix automatico:
```bash
make format    # ruff format . + ruff check --fix .
make lint      # ruff check .
```

### 2. Test con Coverage

```bash
make test          # pytest (coverage se ejecuta automaticamente via pyproject.toml)
make test-cov      # pytest con reporte detallado de coverage
```

Coverage minimo: **80%** (configurado en `pyproject.toml`). Si coverage < 80%, el test falla.

Para un archivo especifico:
```bash
make test-file file=tests/unit/core/test_reconnection_manager.py
```

### 3. Security Scan

```bash
make security      # bandit + safety
bandit -r app/ -ll  # solo bandit
safety check        # solo dependencias
```

### 4. Validacion por Archivo (script legacy)

```bash
bash scripts/validate_file_complete.sh app/domain/services/signal_generator.py
```

Ejecuta 13 checks: ruff lint, ruff format, safety, flake8, pylint, mypy, bandit, radon CC, radon MI, syntax, imports.

### 5. Pre-commit Hooks (automatico en cada commit)

```bash
pre-commit run --all-files    # ejecutar manualmente
```

Hooks configurados:
- trailing-whitespace, end-of-file-fixer, check-yaml
- **ruff** (lint + formato, reemplaza black/isort/flake8)
- **bandit** (seguridad)
- **detect-secrets** (secretos)

---

## Flujos con Ralph

### 6. AAA Production Pipeline (recomendado)

```bash
ralph -c .ralph/ralph_tasks/34_aaa_production.yml
```

Pipeline de 12 hats que integra Ruff + Aider + OpenHands + Confession Loop. Los backpressure gates verifican automaticamente:
- `ruff check` (lint)
- `ruff format --check` (formato)
- `mypy` (tipos)
- `bandit` + `safety` (seguridad)
- `pytest --cov-fail-under=80` (coverage)

Los hooks de Ralph ejecutan `ruff check` y `mypy` automaticamente despues de cada edicion de archivo.

### 7. Production Audit (legacy)

```bash
ralph -c .ralph/ralph_tasks/31_production_audit.yml
```

Pipeline de 10 hats sin integracion con Aider/OpenHands.

### 8. Confession Loop (self-audit)

```bash
ralph run -H .ralph/presets/confession-loop.yml -c .ralph/ralph.yml
```

Pipeline de 4 hats que revisan el codigo desde perspectivas diferentes:
1. **Critic** (30%) - encuentra defectos, anti-patrones, edge cases
2. **Architect** (25%) - evalua SOLID, dependencias, interfaces
3. **Engineer** (25%) - verifica correccion, tipos, concurrencia
4. **Steward** (20%) - revisa seguridad, backwards compatibility

Resultado: confidence score. Si < 80%, se bloquea y se reintenta.

### 9. TDD Red-Green

```bash
ralph run -H .ralph/presets/tdd-red-green.yml -c .ralph/ralph.yml
```

Para nueva funcionalidad: escribe test fallando (red) -> implementa (green) -> refactoriza.

### 10. Debug

```bash
ralph run -H .ralph/presets/debug.yml -c .ralph/ralph.yml
```

Para investigar bugs: investiga -> fix -> verifica.

### 11. Spec-Driven

```bash
ralph run -H .ralph/presets/spec-driven.yml -c .ralph/ralph.yml
```

Para features complejos: spec -> implement -> verify.

### 12. Refactor

```bash
ralph run -H .ralph/presets/refactor.yml -c .ralph/ralph.yml
```

Para refactoring seguro: analiza -> planifica -> ejecuta -> verifica.

---

## Flujos con OpenHands

### 13. Resolver GitHub Issues automaticamente

```bash
# Instalar (solo primera vez)
docker pull ghcr.io/all-hands-ai/openhands:main

# Resolver un issue
openhands resolve --repo mikeyobrien/algoTrading --issue 42

# Resolver todos los issues abiertos
openhands resolve --repo mikeyobrien/algoTrading --all-issues
```

OpenHands:
- Clona el repo
- Analiza el issue
- Implementa el fix
- Crea un PR automaticamente

**Microagent configurado** en `.openhands/microagents/algotrading.md` con conocimiento del proyecto.

### 14. Flujo Ralph + OpenHands

```
Ralph (detecta problemas via backpressure)
  -> Crea GitHub Issues
    -> OpenHands (resuelve automaticamente)
      -> Ralph (valida la solucion con backpressure gates)
```

---

## Flujos con Aider

### 15. Fix puntual interactivo

```bash
# Instalar (solo primera vez)
pip install aider-chat

# Fix rapido de un archivo
aider app/domain/services/signal_generator.py

# Fix con instruccion especifica
aider --message "Refactoriza usando Protocol-based interfaces" app/domain/services/execution/order_manager.py

# Fix con contexto de todo el repo
aider --map-repo
```

**Configuracion** en `.aider.conf.yml`:
- Model: `claude-sonnet-4-20250514`
- Auto-lint con `ruff check --fix` + `ruff format` despues de cada cambio
- Auto-test con `pytest tests/ -x -q --tb=short`

### 16. Flujo Ralph + Aider

```
Ralph (detecta problema via memories/hooks)
  -> Abres Aider para fix interactivo
    -> Aider modifica el codigo
      -> Ralph (valida con backpressure gates)
```

---

## Flujo Completo de Produccion

### Paso 1: Quick Check

```bash
make quality
```

Si falla, fix con:
```bash
make format
make lint
```

### Paso 2: Tests con Coverage

```bash
make test-cov
```

Si coverage < 80%, escribir mas tests.

### Paso 3: AAA Production Pipeline con Ralph

```bash
ralph -c .ralph/ralph_tasks/34_aaa_production.yml
```

Pipeline completo de 12 hats que integra Ruff + Aider + OpenHands + Confession Loop.

### Paso 4: Commit

```bash
git add -A
git commit -m "feat: produccion-ready"
```

Pre-commit hooks se ejecutan automaticamente (ruff, bandit, detect-secrets).

### Paso 5: CI/CD en GitHub

Push a `develop` o `main` activa automaticamente:

```bash
git push origin develop
```

CI/CD pipeline (`.github/workflows/ci-cd.yml`):
- `ruff check` + `ruff format --check`
- `mypy app/`
- `bandit` + `safety`
- `pytest` con coverage >= 80% (Python 3.9, 3.10, 3.11)
- Docker build + push a GHCR
- Deploy a staging (develop) o produccion (main)

---

## Comandos de Referencia Rapida

| Comando | Que hace |
|---|---|
| `make quality` | lint + format check + typecheck + security |
| `make format` | formatea y fix lint automatico |
| `make test` | ejecuta tests con coverage |
| `make test-cov` | tests con reporte detallado |
| `make security` | bandit + safety scan |
| `make check` | quality + test (todo) |
| `ralph -c .ralph/ralph_tasks/34_aaa_production.yml` | **AAA production pipeline (recomendado)** |
| `ralph -c .ralph/ralph_tasks/31_production_audit.yml` | audit completo (legacy) |
| `ralph run -H .ralph/presets/confession-loop.yml -c .ralph/ralph.yml` | self-audit |
| `ralph run -H .ralph/presets/tdd-red-green.yml -c .ralph/ralph.yml` | TDD |
| `aider <archivo>` | fix interactivo con AI |
| `pre-commit run --all-files` | ejecutar hooks manualmente |
| `bash scripts/validate_file_complete.sh <file>` | validar un archivo |

---

## Backpressure Gates de Ralph (configurados)

Estos gates se verifican automaticamente en cada iteracion de Ralph:

| Gate | Comando | Bloquea? |
|--- |---|---|
| tests | `pytest tests/ -x --tb=short -q` | Si |
| typecheck | `mypy app/ --ignore-missing-imports` | Si |
| lint | `ruff check app/` | Si |
| format | `ruff format --check app/` | Si |
| security | `bandit -r app/ -ll` | Si |
| dependencies | `safety check` | Warning |
| coverage | `coverage report --fail-under=80` | Si |

---

## Herramientas Instaladas

| Herramienta | Version | Proposito |
|--- |---|---|
| ruff | 0.14+ | Lint + formato (reemplaza black, isort, flake8) |
| mypy | 1.19+ | Type checking estatico |
| pytest | 8.0+ | Testing framework |
| pytest-cov | 5.0+ | Coverage de tests |
| bandit | 1.8+ | Security linting |
| safety | 3.2+ | Vulnerabilidades en dependencias |
| pre-commit | 3.8+ | Git hooks automatizados |
| ralph | 2.8.1 | Orquestacion de agentes |
| aider | latest | AI pair programming |
| openhands | latest | Resolucion autonomica de issues |
