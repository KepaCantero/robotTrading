# CWC-6556: Implementar Trigger Actions Faltantes

## 📋 Resumen de la Épica

Esta épica implementa los trigger actions faltantes en el sistema de workflows para completar la funcionalidad de automatización. Los trigger actions permiten automatizar respuestas a eventos del sistema sin intervención manual.

## 🎯 Objetivo

Completar la implementación de todos los trigger actions documentados en Connect, asegurando consistencia y funcionalidad completa del sistema de automatización de workflows.

## 📊 Estado Actual

### ✅ Trigger Actions Ya Implementados

- `change-state` - Cambio de estado
- `approve` - Aprobaciones
- `reject` - Rechazos
- `assign` - Asignaciones
- `unassign` - Desasignaciones
- `set-expiration` - Establecer expiración
- `clear-expiration` - Limpiar expiración
- `expire` - Forzar expiración
- `set-message` - Establecer mensajes
- `clean-messages` - Limpiar mensajes
- `remove-restrictions` - Remover restricciones
- `publish-page` - Publicar páginas
- `send-email` - Enviar emails
- `add-labels` - Agregar etiquetas
- `remove-labels` - Remover etiquetas
- `clean-labels` - Limpiar etiquetas

### ❌ Trigger Actions Faltantes (8 total)

## 🚀 Tareas de Implementación

### 1. **remove-message** ✅ (Ya implementado - Solo uso interno)

- **Estado**: Implementado
- **Descripción**: Elimina un mensaje específico de la lista usando su UUID generado
- **Parámetros**:
  - `id` (string) - UUID del mensaje a eliminar
- **Comportamiento**:
  - Busca el mensaje por su ID único
  - Lo elimina de la lista de mensajes activos
  - No afecta otros mensajes

### 2. **log** ✅ (Ya implementado - Solo uso interno)

- **Estado**: Implementado
- **Descripción**: Logger simple de consola backend que imprime un mensaje colorido
- **Parámetros**:
  - `message` (string) - Mensaje a mostrar en los logs
  - `color` (string) - Color del texto
  - `backgroundColor` (string) - Color de fondo del mensaje
  - `modifier` (string) - Modificadores de chalk
- **Comportamiento**:
  - Imprime el mensaje en la consola del servidor
  - Útil para debugging y seguimiento de workflows
  - Solo visible para administradores del sistema

### 3. **set-restrictions** (Nuevo - A implementar)

- **Estado**: Pendiente
- **Descripción**: Establece restricciones de acceso o permisos específicos para un contenido
- **Parámetros**:
  - `contentId` (string, opcional) - ID del contenido a restringir
  - `restrictions` (array) - Lista de restricciones a aplicar
  - `type` (enum) - Tipo de restricción: view, edit, comment, delete
  - `users` (array, opcional) - Lista de usuarios afectados
  - `groups` (array, opcional) - Lista de grupos afectados
- **Comportamiento**:
  - Aplica restricciones de acceso al contenido especificado
  - Puede restringir por usuarios individuales o grupos
  - Las restricciones pueden ser de diferentes tipos

### 4. **add-restrictions** (Nuevo - A implementar)

- **Estado**: Pendiente
- **Descripción**: Añade restricciones adicionales a las existentes sin eliminar las actuales
- **Parámetros**:
  - `contentId` (string, opcional) - ID del contenido
  - `restrictions` (array) - Nuevas restricciones a añadir
  - `type` (enum) - Tipo de restricción
  - `users` (array, opcional) - Usuarios adicionales a restringir
  - `groups` (array, opcional) - Grupos adicionales a restringir
- **Comportamiento**:
  - Mantiene las restricciones existentes
  - Añade nuevas restricciones a la lista actual
  - Útil para restricciones progresivas en workflows

### 5. **set-metadata** (Nuevo - A implementar)

- **Estado**: Pendiente
- **Descripción**: Establece metadatos específicos para un contenido o página
- **Parámetros**:
  - `contentId` (string, opcional) - ID del contenido
  - `metadata` (object) - Objeto con los metadatos a establecer
  - `overwrite` (boolean, opcional) - Si sobrescribir metadatos existentes (default: true)
- **Comportamiento**:
  - Establece metadatos personalizados en el contenido
  - Puede sobrescribir o preservar metadatos existentes
  - Útil para tracking, categorización, o información adicional

### 6. **increment-metadata** (Nuevo - A implementar)

- **Estado**: Pendiente
- **Descripción**: Incrementa valores numéricos en metadatos existentes
- **Parámetros**:
  - `contentId` (string, opcional) - ID del contenido
  - `metadata` (object) - Objeto con los campos a incrementar y sus valores
  - `createIfNotExists` (boolean, opcional) - Crear el campo si no existe (default: false)
- **Comportamiento**:
  - Incrementa valores numéricos en metadatos
  - Útil para contadores, versiones, o tracking de eventos
  - Puede crear nuevos campos o solo modificar existentes

### 7. **copy-page** (Nuevo - A implementar)

- **Estado**: Pendiente
- **Descripción**: Crea una copia de una página o contenido en una ubicación específica
- **Parámetros**:
  - `sourceContentId` (string) - ID del contenido a copiar
  - `targetSpaceKey` (string, opcional) - Espacio de destino
  - `targetParentId` (string, opcional) - Página padre de destino
  - `newTitle` (string, opcional) - Nuevo título para la copia
  - `copyAttachments` (boolean, opcional) - Copiar adjuntos (default: true)
  - `copyComments` (boolean, opcional) - Copiar comentarios (default: false)
- **Comportamiento**:
  - Crea una copia exacta del contenido especificado
  - Puede cambiar el título y ubicación
  - Opciones para incluir/excluir adjuntos y comentarios
  - Útil para templates, versiones, o duplicación de contenido

### 8. **webhook** (Nuevo - A implementar)

- **Estado**: Pendiente
- **Descripción**: Envía una petición HTTP a una URL externa con datos del workflow
- **Parámetros**:
  - `url` (string) - URL del webhook a llamar
  - `method` (enum) - Método HTTP: GET, POST, PUT, PATCH (default: POST)
  - `headers` (object, opcional) - Headers HTTP adicionales
  - `payload` (object, opcional) - Datos a enviar en el body
  - `timeout` (number, opcional) - Timeout en milisegundos (default: 30000)
  - `retryAttempts` (number, opcional) - Número de reintentos (default: 3)
- **Comportamiento**:
  - Envía petición HTTP a sistema externo
  - Incluye contexto del workflow y contenido
  - Maneja reintentos y timeouts
  - Útil para integraciones con sistemas externos

## 🏗️ Arquitectura de Implementación

### Patrón de Implementación

Cada trigger action sigue el patrón establecido:

1. **Definición en ITrigger.ts** - Agregar al tipo `Actions`
2. **Implementación en ActionFactory** - Crear instancia del action
3. **Clase Action específica** - Implementar lógica de negocio
4. **Tests unitarios** - Verificar funcionalidad
5. **Tests de integración** - Verificar en contexto completo

### Estructura de Archivos

```
packages/workflow-engine/src/engine/services/actions/
├── SetRestrictionsAction.ts
├── AddRestrictionsAction.ts
├── SetMetadataAction.ts
├── IncrementMetadataAction.ts
├── CopyPageAction.ts
└── WebhookAction.ts
```

## 📋 Criterios de Aceptación

### Para cada Trigger Action:

- [ ] Definido en `ITrigger.ts` con tipos correctos
- [ ] Implementado en `ActionFactory`
- [ ] Clase Action con lógica completa
- [ ] Validación de parámetros requeridos
- [ ] Manejo de errores apropiado
- [ ] Logging para debugging y auditoría
- [ ] Tests unitarios con cobertura > 90%
- [ ] Tests de integración
- [ ] Documentación actualizada

### Criterios Generales:

- [ ] Consistencia con patrón existente
- [ ] Compatibilidad con value references
- [ ] Performance adecuada
- [ ] Seguridad en parámetros
- [ ] Manejo de casos edge

## 🎯 Priorización

### Alta Prioridad:

1. **set-restrictions** - Funcionalidad crítica de permisos
2. **add-restrictions** - Complemento necesario
3. **webhook** - Integración con sistemas externos

### Media Prioridad:

4. **set-metadata** - Gestión de metadatos
5. **increment-metadata** - Tracking y contadores

### Baja Prioridad:

6. **copy-page** - Funcionalidad de contenido

## 📝 Notas de Implementación

### Triggers ya implementados (remove-message, log):

- Estos ya existen pero son de uso interno
- Pueden usarse como referencia para la implementación

### Consistencia con el patrón existente:

- Todos los nuevos triggers siguen el mismo patrón de los existentes
- Incluyen `action`, parámetros específicos, y manejo de errores

### Parámetros opcionales:

- Muchos parámetros son opcionales para mantener flexibilidad
- Siguen el patrón de los triggers existentes

### Validación:

- Cada trigger debe validar sus parámetros requeridos antes de ejecutarse

### Logging:

- Todos los triggers deben incluir logging apropiado para debugging y auditoría

## 🔗 Referencias

- [Trigger System Documentation](../docs/trigger-system.md)
- [Action Patterns](../docs/action-patterns.md)
- [Integration Tests](../tests/integration/trigger-actions/)
- [Connect Documentation](https://connect.appfire.com/docs/trigger-actions)

## 📅 Timeline Estimado

- **Fase 1** (Alta Prioridad): 2-3 semanas
- **Fase 2** (Media Prioridad): 1-2 semanas
- **Fase 3** (Baja Prioridad): 1 semana
- **Total**: 4-6 semanas

## 👥 Equipo

- **Tech Lead**: Kepa Cantero
- **Developers**: TBD
- **QA**: TBD
- **Product Owner**: TBD
