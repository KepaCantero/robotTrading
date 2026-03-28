#!/usr/bin/env python3
"""
Script de verificación de librerías críticas de trading.

Comprueba que las siguientes librerías están instaladas y funcionan:
- quantstats
- empyrical-reloaded
- pyfolio-reloaded
- FinRL
- PyPortfolioOpt
- alphalens-reloaded
"""

import sys
from typing import Dict, Any
from pathlib import Path

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("VERIFICACIÓN DE LIBRERÍAS CRÍTICAS DE TRADING")
print("=" * 80)
print()

# Diccionario para almacenar resultados
results: Dict[str, Dict[str, Any]] = {}

# Librerías a verificar con sus funciones de prueba
libraries_to_check = {
    'quantstats': {
        'import_name': 'quantstats',
        'version_attr': '__version__',
        'test_function': lambda: hasattr(__import__('quantstats'), 'reports'),
        'required': True,
    },
    'empyrical-reloaded': {
        'import_name': 'empyrical',
        'version_attr': '__version__',
        'test_function': lambda: __import__('empyrical').sharpe_ratio(
            pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
        ),
        'required': True,
    },
    'pyfolio-reloaded': {
        'import_name': 'pyfolio',
        'version_attr': '__version__',
        'test_function': lambda: __import__('pyfolio').timeseries.perf_stats(
            pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
        ),
        'required': True,
    },
    'FinRL': {
        'import_name': 'finrl',
        'version_attr': '__version__',
        'test_function': lambda: hasattr(__import__('finrl'), 'env'),
        'required': False,  # Fase 2
    },
    'PyPortfolioOpt': {
        'import_name': 'pypfopt',
        'version_attr': '__version__',
        'test_function': lambda: hasattr(__import__('pypfopt'), 'EfficientFrontier'),
        'required': False,  # Fase 2
    },
    'alphalens-reloaded': {
        'import_name': 'alphalens',
        'version_attr': '__version__',
        'test_function': lambda: hasattr(__import__('alphalens'), 'performance'),
        'required': False,  # Fase 2
    },
}

# Importar pandas y numpy que son dependencias comunes
try:
    import pandas as pd

    print("✅ Dependencias base (pandas) disponibles")
except ImportError as e:
    print(f"❌ Error importando dependencias base: {e}")
    sys.exit(1)

print()

# Verificar cada librería
for lib_name, lib_info in libraries_to_check.items():
    status = {
        'installed': False,
        'importable': False,
        'version': None,
        'test_passed': False,
        'error': None,
        'required': lib_info.get('required', False),
    }

    print(f"📦 Verificando {lib_name}...")

    # 1. Verificar instalación con pip
    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', lib_info['import_name']],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            status['installed'] = True
            # Extraer versión del output
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    status['version'] = line.split(':', 1)[1].strip()
        else:
            status['error'] = f"No instalado según pip"
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        status['error'] = f"Error verificando instalación: {e}"

    # 2. Intentar importar
    try:
        module = __import__(lib_info['import_name'])
        status['importable'] = True

        # 3. Obtener versión si está disponible
        if status['version'] is None:
            try:
                if hasattr(module, lib_info['version_attr']):
                    status['version'] = getattr(module, lib_info['version_attr'])
            except:
                pass

        # 4. Ejecutar función de prueba
        try:
            test_result = lib_info['test_function']()
            status['test_passed'] = True
            print(
                f"   ✅ Test pasado: {test_result if not isinstance(test_result, pd.Series) else 'OK'}"
            )
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            status['error'] = f"Error en test: {type(e).__name__}: {str(e)[:100]}"
            print(f"   ⚠️  Test falló: {e}")

    except ImportError as e:
        status['error'] = f"No se puede importar: {e}"
        print(f"   ❌ No se puede importar: {e}")
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        status['error'] = f"Error inesperado: {type(e).__name__}: {str(e)[:100]}"
        print(f"   ❌ Error: {e}")

    results[lib_name] = status

    # Mostrar resumen por librería
    if status['importable'] and status['test_passed']:
        print(f"   ✅ {lib_name} OK (versión: {status['version'] or 'N/A'})")
    elif status['importable']:
        print(f"   ⚠️  {lib_name} importable pero test falló")
    else:
        print(f"   ❌ {lib_name} no disponible")
    print()

# Resumen final
print("=" * 80)
print("RESUMEN FINAL")
print("=" * 80)
print()

required_ok = 0
required_total = 0
optional_ok = 0
optional_total = 0

for lib_name, status in results.items():
    if status['required']:
        required_total += 1
        if status['importable'] and status['test_passed']:
            required_ok += 1
            print(f"✅ {lib_name} (REQUERIDA) - OK")
        else:
            print(f"❌ {lib_name} (REQUERIDA) - FALTA o FALLA")
            if status['error']:
                print(f"   Error: {status['error']}")
    else:
        optional_total += 1
        if status['importable'] and status['test_passed']:
            optional_ok += 1
            print(f"✅ {lib_name} (OPCIONAL) - OK")
        elif status['importable']:
            print(f"⚠️  {lib_name} (OPCIONAL) - Importable pero test falló")
            if status['error']:
                print(f"   Error: {status['error']}")
        else:
            print(f"⚪ {lib_name} (OPCIONAL) - No instalada")

print()
print("=" * 80)
print(f"RESUMEN ESTADÍSTICO")
print("=" * 80)
print(f"Librerías requeridas (Fase 1): {required_ok}/{required_total} OK")
print(f"Librerías opcionales (Fase 2): {optional_ok}/{optional_total} OK")
print()

# Determinar estado general
if required_ok == required_total:
    print("🎉 TODAS LAS LIBRERÍAS REQUERIDAS ESTÁN FUNCIONANDO CORRECTAMENTE")
    exit_code = 0
elif required_ok > 0:
    print("⚠️  ALGUNAS LIBRERÍAS REQUERIDAS FALTAN O TIENEN PROBLEMAS")
    exit_code = 1
else:
    print("❌ NINGUNA LIBRERÍA REQUERIDA ESTÁ DISPONIBLE")
    exit_code = 1

print()
print("=" * 80)
print("RECOMENDACIONES")
print("=" * 80)

# Mostrar comandos de instalación para librerías faltantes
missing_required = [
    lib
    for lib, status in results.items()
    if status['required'] and not (status['importable'] and status['test_passed'])
]
missing_optional = [
    lib for lib, status in results.items() if not status['required'] and not status['importable']
]

if missing_required:
    print("\n📦 Instalar librerías requeridas faltantes:")
    for lib in missing_required:
        lib_map = {
            'quantstats': 'quantstats',
            'empyrical-reloaded': 'empyrical-reloaded',
            'pyfolio-reloaded': 'pyfolio-reloaded',
        }
        print(f"   pip install {lib_map.get(lib, lib)}")

if missing_optional:
    print("\n📦 Instalar librerías opcionales (Fase 2):")
    for lib in missing_optional:
        lib_map = {
            'FinRL': 'finrl',
            'PyPortfolioOpt': 'PyPortfolioOpt',
            'alphalens-reloaded': 'alphalens-reloaded',
        }
        print(f"   pip install {lib_map.get(lib, lib)}")

print()

sys.exit(exit_code)
