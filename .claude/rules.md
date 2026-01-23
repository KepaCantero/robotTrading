# Reglas de Arquitectura y Implementación — LinguaForge

> Última actualización: 2025-01-XX
> Basado en: Memory Bank completo (systemPatterns.md, techContext.md, activeContext.md, MASTER_PLAN.md)

## 🚫 PROHIBICIONES ABSOLUTAS

### NO MOCKS, NO DATOS FALSOS, NO ALUCINACIONES

1. **NUNCA crear datos mock o de ejemplo**:
   - ❌ NO usar `mockData`, `sampleData`, `fakeData`, `dummyData`
   - ❌ NO crear arrays hardcodeados con datos de ejemplo
   - ❌ NO usar `TODO: implementar` sin implementación real
   - ✅ SIEMPRE usar datos reales de stores, servicios o APIs

2. **NUNCA inventar funcionalidad**:
   - ❌ NO asumir que existe un servicio/store si no está documentado
   - ❌ NO crear funciones "placeholder" sin implementación completa
   - ✅ SIEMPRE verificar existencia en memory bank antes de usar
   - ✅ SIEMPRE leer archivos existentes antes de modificar

3. **NUNCA alucinar sobre la arquitectura**:
   - ❌ NO crear nuevos stores sin verificar necesidad en MASTER_PLAN.md
   - ❌ NO cambiar patrones establecidos sin justificación
   - ✅ SIEMPRE seguir estructura de directorios documentada
   - ✅ SIEMPRE usar patrones existentes (Store Pattern, Service Pattern, Schema-First)

## ✅ REGLAS DE IMPLEMENTACIÓN REAL

### 1. Verificación Pre-Implementación

**ANTES de escribir código, SIEMPRE:**

1. **Leer Memory Bank completo:**
   - `.memory-bank/systemPatterns.md` - Patrones arquitectónicos
   - `.memory-bank/techContext.md` - Stack tecnológico
   - `.memory-bank/activeContext.md` - Estado actual
   - `.memory-bank/MASTER_PLAN.md` - Plan de tareas
   - `.memory-bank/DISEÑO_STRATEGY.md` - Estrategia de diseño visual

2. **Verificar existencia de código relacionado:**
   - Buscar stores existentes en `src/store/`
   - Buscar servicios existentes en `src/services/`
   - Buscar componentes similares en `src/components/`
   - Verificar schemas en `src/schemas/`

3. **Leer archivos relacionados:**
   - Leer el archivo que se va a modificar completamente
   - Leer imports y dependencias
   - Verificar tipos TypeScript existentes

### 2. Arquitectura Estricta

#### Estructura de Directorios (FIJA)

```
src/
├── app/                    # Next.js App Router pages
│   ├── (auth)/            # Rutas de autenticación
│   ├── learn/             # Sistema de aprendizaje principal
│   ├── input/             # Sistema INPUT (video/audio/texto)
│   ├── decks/              # Sistema SRS
│   ├── profile/           # Perfil de usuario
│   └── api/               # API routes
├── components/            # Componentes React
│   ├── exercises/        # Ejercicios de aprendizaje
│   ├── transcript/        # Componentes de transcripción
│   ├── layout/           # Componentes de layout
│   └── shared/           # Componentes compartidos
├── store/                # Zustand stores
├── services/             # Servicios y lógica de negocio
├── schemas/              # Schemas Zod
├── types/                # TypeScript types
└── lib/                  # Utilidades
```

**NO crear nuevos directorios sin justificación en MASTER_PLAN.md**

#### Convenciones de Naming (FIJAS)

- **Componentes:** PascalCase (`WordSelector.tsx`)
- **Stores:** camelCase con `use` prefix (`useSRSStore.ts`)
- **Services:** camelCase (`wordExtractor.ts`)
- **Types:** camelCase (`srs.ts`)
- **Schemas:** camelCase (`content.ts`)

### 3. Patrones de Diseño Obligatorios

#### Store Pattern (Zustand)

**SIEMPRE usar este patrón para stores:**

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useNewStore = create<NewStoreType>()(
  persist(
    (set, get) => ({
      // Estado inicial
      data: [],
      
      // Acciones
      addItem: (item) => set((state) => ({
        data: [...state.data, item]
      })),
      
      // Getters computados
      getStats: () => {
        const state = get();
        return { /* cálculos reales */ };
      },
    }),
    { 
      name: 'new-storage', // Nombre único para persistencia
    }
  )
);
```

**REGLAS:**
- ✅ SIEMPRE usar `persist` middleware para persistencia local
- ✅ SIEMPRE definir tipos TypeScript explícitos
- ✅ SIEMPRE usar `get()` para acceder a estado en acciones
- ❌ NUNCA usar `useState` para estado global compartido

#### Service Pattern

**SIEMPRE usar este patrón para servicios:**

```typescript
// src/services/newService.ts

/**
 * Descripción clara del propósito del servicio
 */

export interface ServiceInput {
  // Tipos explícitos
}

export interface ServiceOutput {
  // Tipos explícitos
}

/**
 * Función principal del servicio
 * @param input - Descripción del parámetro
 * @returns Descripción del retorno
 */
export function serviceFunction(input: ServiceInput): ServiceOutput {
  // Implementación REAL, no mock
  // Usar datos reales de stores o APIs
  // Manejar errores apropiadamente
  
  return {
    // Datos reales procesados
  };
}
```

**REGLAS:**
- ✅ SIEMPRE funciones puras cuando sea posible
- ✅ SIEMPRE tipos TypeScript explícitos
- ✅ SIEMPRE documentación JSDoc
- ✅ SIEMPRE manejo de errores
- ❌ NUNCA dependencias de React en servicios
- ❌ NUNCA datos mock o hardcodeados

#### Schema-First Pattern (Zod)

**SIEMPRE definir schemas antes de tipos:**

```typescript
// src/schemas/newSchema.ts

import { z } from 'zod';

export const NewItemSchema = z.object({
  id: z.string(),
  name: z.string().min(1),
  // ... más campos
});

export type NewItem = z.infer<typeof NewItemSchema>;
```

**REGLAS:**
- ✅ SIEMPRE definir schema Zod primero
- ✅ SIEMPRE inferir tipos TypeScript desde schema
- ✅ SIEMPRE validar datos con schema antes de usar
- ❌ NUNCA tipos TypeScript sin schema Zod correspondiente

### 4. Integración con Stores Existentes

**Stores disponibles (verificar antes de crear nuevo):**

- `useSRSStore` - Sistema de repaso espaciado (SM-2)
- `useInputStore` - Métricas de input comprensible (Krashen)
- `useImportedNodesStore` - Contenido importado por usuario
- `useWordDictionaryStore` - Palabras estudiadas
- `useUserStore` - Configuración de usuario (modo guiado/autónomo)
- `useGamificationStore` - XP, coins, gems, streak
- `useCognitiveLoadStore` - Carga cognitiva (CLT)
- `useWarmupStore` - Calentamientos cognitivos
- `useMissionStore` - Sistema de misiones

**ANTES de crear nuevo store:**
1. Verificar si existe store similar
2. Verificar si se puede extender store existente
3. Verificar necesidad en MASTER_PLAN.md
4. Leer store existente para entender patrón

### 5. Integración con Servicios Existentes

**Servicios disponibles:**

- `generateExercisesFromPhrases.ts` - Genera ejercicios desde frases
- `wordExtractor.ts` - Extrae palabras clave (verbos, sustantivos, etc.)
- `translationService.ts` - Traducción automática
- `conjugationService.ts` - Conjugación de verbos franceses
- `cognitiveLoadMetrics.ts` - Métricas de carga cognitiva
- `youtubeTranscriptService.ts` - Extracción de transcripciones YouTube

**ANTES de crear nuevo servicio:**
1. Verificar si existe servicio similar
2. Leer servicio existente para entender patrón
3. Reutilizar funciones existentes cuando sea posible

### 6. Stack Tecnológico (FIJO)

**NO cambiar estas tecnologías sin justificación:**

- **Framework:** Next.js 14 (App Router) - NO cambiar a Pages Router
- **Estado:** Zustand 4+ - NO usar Redux, Context API para estado global
- **Estilos:** Tailwind CSS 3+ - NO usar CSS modules, styled-components
- **Animaciones:** Framer Motion 10+ - NO usar otras librerías de animación
- **Validación:** Zod 4+ - NO usar otras librerías de validación
- **Tipos:** TypeScript strict mode - NO usar `any`, `@ts-ignore`

**Nuevas tecnologías permitidas (solo si están en DISEÑO_STRATEGY.md):**
- Rive (para visualización neuronal)
- Lordicon (para iconografía animada)
- LottieFiles (para celebraciones)
- Google Fonts (Quicksand, Inter)

### 7. Implementación de Componentes

**Estructura obligatoria para componentes:**

```typescript
'use client'; // Solo si necesita interactividad del cliente

import { ... } from '...';

// Types
interface ComponentProps {
  // Props explícitas con tipos
}

// Component
export function Component({ ... }: ComponentProps) {
  // 1. Hooks (useState, useEffect, etc.)
  // 2. Stores (useSRSStore, etc.)
  // 3. State local
  // 4. Effects
  // 5. Handlers
  // 6. Render
  
  return (
    // JSX real, no placeholder
  );
}
```

**REGLAS:**
- ✅ SIEMPRE tipos TypeScript explícitos para props
- ✅ SIEMPRE usar stores existentes para datos globales
- ✅ SIEMPRE manejar estados de carga y error
- ✅ SIEMPRE validar props con Zod si vienen de API
- ❌ NUNCA datos mock en componentes
- ❌ NUNCA `console.log` en producción (usar solo para debugging temporal)

### 8. API Routes

**Patrón obligatorio para API routes:**

```typescript
// src/app/api/new/route.ts

import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // 1. Validar parámetros
    // 2. Llamar a servicio real
    // 3. Manejar errores
    // 4. Retornar respuesta
    
    return NextResponse.json({ data: realData });
  } catch (error) {
    return NextResponse.json(
      { error: 'Mensaje de error claro' },
      { status: 500 }
    );
  }
}
```

**REGLAS:**
- ✅ SIEMPRE manejo de errores con try-catch
- ✅ SIEMPRE validar entrada con Zod
- ✅ SIEMPRE retornar errores apropiados
- ✅ SIEMPRE usar servicios reales, no mocks
- ❌ NUNCA datos hardcodeados en respuestas
- ❌ NUNCA exponer información sensible en errores

### 9. Manejo de Datos

**SIEMPRE usar datos reales:**

1. **De Stores:**
   ```typescript
   const cards = useSRSStore((state) => state.cards);
   // NO: const cards = mockCards;
   ```

2. **De APIs:**
   ```typescript
   const response = await fetch('/api/real-endpoint');
   const data = await response.json();
   // NO: const data = { mock: 'data' };
   ```

3. **De Servicios:**
   ```typescript
   const words = wordExtractor.extractKeywords(realPhrases);
   // NO: const words = ['mock', 'words'];
   ```

### 10. Validación y Tipos

**SIEMPRE validar datos:**

1. **En API routes:**
   ```typescript
   const schema = z.object({ ... });
   const validated = schema.parse(requestBody);
   ```

2. **En componentes:**
   ```typescript
   if (!data || !Array.isArray(data)) {
     return <ErrorState />;
   }
   ```

3. **En servicios:**
   ```typescript
   if (!input || typeof input !== 'string') {
     throw new Error('Input must be a string');
   }
   ```

### 11. Testing (Futuro)

**Cuando se implementen tests:**

- ✅ Tests unitarios para servicios (funciones puras)
- ✅ Tests de integración para flujos principales
- ✅ Tests E2E para flujos de usuario críticos
- ❌ NO tests con datos mock sin justificación
- ❌ NO tests que no prueben funcionalidad real

## 📋 CHECKLIST PRE-IMPLEMENTACIÓN

**ANTES de escribir cualquier código:**

- [ ] Leí `.memory-bank/systemPatterns.md`
- [ ] Leí `.memory-bank/techContext.md`
- [ ] Leí `.memory-bank/activeContext.md`
- [ ] Verifiqué si existe código similar
- [ ] Leí archivos relacionados completamente
- [ ] Verifiqué estructura de directorios correcta
- [ ] Verifiqué convenciones de naming
- [ ] Verifiqué stack tecnológico permitido
- [ ] Planifiqué uso de stores/servicios existentes
- [ ] Definí schema Zod si es necesario
- [ ] Planifiqué manejo de errores
- [ ] NO usaré datos mock o falsos

## 🎯 PRINCIPIOS FUNDAMENTALES

1. **Real sobre Mock:** Siempre implementación real, nunca datos falsos
2. **Verificar antes de Crear:** Leer memory bank y código existente
3. **Seguir Patrones:** Usar patrones establecidos, no inventar nuevos
4. **Tipos Explícitos:** TypeScript strict, sin `any` ni `@ts-ignore`
5. **Validación Siempre:** Zod schemas para validación en runtime
6. **Manejo de Errores:** Try-catch apropiado, mensajes claros
7. **Documentación:** JSDoc para funciones públicas
8. **Arquitectura Consistente:** Seguir estructura establecida

## ⚠️ SEÑALES DE ALERTA

**Si encuentras estas señales, DETENTE y verifica:**

- 🔴 Creando datos mock o de ejemplo
- 🔴 Asumiendo existencia de código sin verificar
- 🔴 Creando nuevos stores sin necesidad documentada
- 🔴 Cambiando patrones establecidos sin justificación
- 🔴 Usando tecnologías no documentadas en techContext.md
- 🔴 Creando directorios fuera de estructura establecida
- 🔴 Implementando funcionalidad sin leer código relacionado

## 📚 REFERENCIAS OBLIGATORIAS

**Antes de implementar, consultar:**

1. `.memory-bank/systemPatterns.md` - Patrones arquitectónicos
2. `.memory-bank/techContext.md` - Stack tecnológico
3. `.memory-bank/activeContext.md` - Estado actual del proyecto
4. `.memory-bank/MASTER_PLAN.md` - Plan de tareas y fases
5. `.memory-bank/DISEÑO_STRATEGY.md` - Estrategia de diseño visual
6. Código existente en `src/` - Para entender implementaciones reales

---

**Última actualización:** 2025-01-XX  
**Versión:** 1.0  
**Mantener estas reglas actualizadas según evolucione el proyecto**

