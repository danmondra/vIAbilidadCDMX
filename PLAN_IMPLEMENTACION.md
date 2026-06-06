# Plan de Implementación: ViableCDMX
## Asesor Virtual de Viabilidad y Trámites para Negocios en CDMX

**Versión:** 1.0  
**Fecha:** Junio 2026  
**Contexto:** Hackathon NVIDIA/SEDECO — Reto 2: Viabilidad de Negocios CDMX  
**Áreas:** (1) Bot conversacional — Telegram (@vIAbilibot); (2) Dashboard Web — Radar CDMX

### Decisiones de alcance actualizadas

Estas decisiones mandan sobre el resto del plan:

- **MVP primero:** bot conversacional + dashboard mínimo usable + ruta de trámites.
- **Extras al final si hay tiempo:** implementación completa de los módulos B y C del dashboard, score detallado vía API, integraciones API con RETYS/SIAPEM.
- **Radar MVP:** solo usa **competencia**, **rentabilidad** y **gastos fijos**. Se eliminan del radar MVP afluencia, inversión, empleos y apoyo legal.
- **Uso de suelo:** se consume desde **CSV local en la carpeta del proyecto**; no se depende de API SEDUVI para la demo.
- **RETYS/SIAPEM:** se tratan como fuentes documentales, enlaces y guías de trámite. No asumimos que exista acceso API.
- **Bot:** se elimina el módulo de **negocios guardados** para reducir persistencia, complejidad y riesgo de datos personales.

---

## Índice

1. [Visión General y Arquitectura](#1-visión-general-y-arquitectura)
2. [Datos y Fuentes Oficiales](#2-datos-y-fuentes-oficiales)
3. [Área 1 — Bot Conversacional (Telegram @vIAbilibot)](#3-área-1--bot-conversacional-telegram--vIAbilibot)
4. [Área 2 — Dashboard Web (Radar CDMX)](#4-área-2--dashboard-web-radar-cdmx)
5. [Capa de IA y RAG](#5-capa-de-ia-y-rag)
6. [Base de Datos y Estado](#6-base-de-datos-y-estado)
7. [API Backend Compartido](#7-api-backend-compartido)
8. [Lógica de Negocio Central](#8-lógica-de-negocio-central)
9. [Fases de Implementación](#9-fases-de-implementación)
10. [Stack Tecnológico Consolidado](#10-stack-tecnológico-consolidado)
11. [Estructura de Archivos del Proyecto](#11-estructura-de-archivos-del-proyecto)
12. [Detalles Técnicos por Módulo](#12-detalles-técnicos-por-módulo)
13. [Casos Edge y Manejo de Errores](#13-casos-edge-y-manejo-de-errores)
14. [Canal de Comunicación](#14-canal-de-comunicación)
15. [Criterios de Aceptación y Demo](#15-criterios-de-aceptación-y-demo)

---

## 1. Visión General y Arquitectura

### Problema que resuelve

Los emprendedores en CDMX enfrentan dos barreras al abrir un negocio:

1. **Desconocimiento de viabilidad:** No saben si su giro es rentable en la zona elegida (competencia, uso de suelo, riesgo regulatorio).
2. **Falta de claridad en trámites:** Desconocen qué documentos necesitan, en qué orden tramitarlos y a qué ventanillas acudir, lo que deriva en retrasos, gastos innecesarios, clausuras y sanciones.

### Producto: ViableCDMX

Plataforma dual compuesta por:

- **Bot conversacional** (Telegram @vIAbilibot) que guía al usuario desde la idea de negocio hasta el checklist de trámites personalizado.
- **Dashboard Web** (Radar CDMX) que visualiza datos territoriales, análisis de viabilidad y ruta de trámites de forma interactiva para agentes SEDECO o emprendedores con acceso web.

### Diagrama de Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND / CANALES                    │
│  ┌──────────────┐              ┌───────────────────────┐ │
│  │  Bot Telegram │              │   Dashboard Web HTML  │ │
│  │  @vIAbilibot │              │   (Radar CDMX)        │ │
│  └──────┬───────┘              └──────────┬────────────┘ │
└─────────┼────────────────────────────────┼──────────────┘
          │ HTTPS / Webhook                │ HTTP REST
┌─────────▼────────────────────────────────▼──────────────┐
│                    BACKEND (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Bot Handler  │  │ Viabilidad   │  │ Trámites API   │ │
│  │ (Fsm States) │  │ Engine       │  │ (RETYS/SIAPEM) │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │
│         │                 │                   │          │
│  ┌──────▼─────────────────▼───────────────────▼────────┐ │
│  │              Capa de IA / RAG                        │ │
│  │  Claude API  /  GPT-4o  +  Vector Store (PDFs)      │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                  Base de Datos                        │ │
│  │   SQLite (dev) / PostgreSQL (prod)                   │ │
│  │   + JSON fixtures (DENUE simulado, giros, trámites)  │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
          │                                │
┌─────────▼──────────────────────────────────────────────┐
│                  FUENTES EXTERNAS                        │
│  DENUE (INEGI) · SEDUVI · SIAPEM · RETYS · Finanzas    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Datos y Fuentes Oficiales

### 2.1 Fuentes de datos a integrar

| Fuente | Contenido | URL | Forma de consumo |
|--------|-----------|-----|-----------------|
| **DENUE (INEGI)** | Establecimientos mercantiles activos por SCIAN, colonia, alcaldía | https://www.inegi.org.mx/app/descarga/ficha.html?tit=3615697&ag=9&f=csv | CSV descargado + indexado localmente |
| **Uso de Suelo local** | Compatibilidad giro-zona geográfica | CSV local del proyecto | Lectura local + normalización |
| **RETYS CDMX** | Registro de trámites y servicios | https://www.registrodetramitesyservicios.cdmx.gob.mx/ | Links oficiales + fixtures documentales |
| **SIAPEM** | Plataforma de avisos y permisos | https://siapem.cdmx.gob.mx/ | Links directos + guías PDF en RAG |
| **Ley de Establecimientos Mercantiles (LEM)** | Clasificación legal de giros | https://prontuario.cdmx.gob.mx/pdf/Ley%20Establecimientos%20Mercantiles%2024122025.pdf | PDF en RAG |
| **Reglamento LEM** | Detalle regulatorio | https://prontuario.cdmx.gob.mx/pdf/e69b_REGLAMENTO... | PDF en RAG |
| **Finanzas CDMX** | Constancias de no adeudo predial/agua | https://data.finanzas.cdmx.gob.mx/formato_lc | Link directo al usuario |

| **Certificado de Uso de Suelo** | Trámite SEDUVI digital | http://certificadodigital.cdmx.gob.mx:8080/CertificadoDigital/ | Link directo al usuario |

### 2.2 Estrategia de datos para el Hackathon

Dado que es una demo, se acepta y espera el uso de **datos sintéticos plausibles**. La estrategia es:

1. Descargar DENUE CSV real de CDMX (disponible públicamente) y usarlo para competencia real por SCIAN.
2. Para uso de suelo: cargar el CSV local disponible en la carpeta del proyecto y mapearlo a compatibilidad por giro/zona.
3. Para radar MVP: derivar competencia, rentabilidad y gastos fijos con fixtures locales y/o datos ya disponibles.
4. Para trámites: usar los manuales de CENPROIN (ya documentados), RETYS y SIAPEM como fuentes documentales y enlaces oficiales. La integración API queda como extra.

### 2.3 Catálogo de Giros (base para el bot)

Derivado de la LEM y los catálogos RETYS, los giros se mapean en tres categorías:

**Bajo Impacto (Art. 35 LEM) — Formato EM-03:**
Tiendas de abarrotes, estéticas, florerías, papelerías, oficinas, cafeterías, fondas, farmacias, lavanderías, talleres de reparación menor, tortillerías, carnicerías, fruterías, librerías, ferreterías, mueblerías, boutiques de ropa.

**Impacto Vecinal (Art. 19 LEM) — Formato EM-11:**
Salones de fiesta, restaurantes (con o sin venta de alcohol con alimentos), hoteles, clubes privados, cines, autocinemas, teatros, auditorios, gimnasios, spas, consultorios médicos, academias de baile/música.

**Impacto Zonal (Art. 27 Bis LEM) — Formato EM-08 (Solicitud de Permiso, no Aviso):**
Bares, cantinas, antros, discotecas, casinos, cabarets, peñas, chelerías, estadios, establecimientos de entretenimiento para adultos, espacios de diversión nocturnos, establecimientos con bailes eróticos, juegos con apuestas y sorteos.

---

## 3. Área 1 — Bot Conversacional (Telegram @vIAbilibot)

### 3.1 Stack del Bot

- **Framework:** `python-telegram-bot` v22 con `ConversationHandler` (FSM nativo)
- **IA/NLP:** Claude 3.5 Sonnet API (Anthropic) como motor de comprensión y generación de respuestas
- **RAG:** LlamaIndex o LangChain con ChromaDB para búsqueda sobre PDFs oficiales
- **Estado de sesión:** SQLite solo para conversación/flujo activo. No se implementa persistencia de negocios guardados en el MVP.
- **Hosting:** Railway o Render (deploy desde GitHub)

### 3.2 Estados del ConversationHandler (FSM)

```
START
  └─> MENU_PRINCIPAL
        ├─> FLUJO_VIABILIDAD
        │     ├─> ASK_GIRO
        │     ├─> ASK_UBICACION
        │     ├─> ASK_DIMENSIONES
        │     ├─> ASK_ALCOHOL
        │     ├─> PROCESANDO_VIABILIDAD
        │     ├─> MOSTRAR_REPORTE
        │     └─> FLUJO_TRAMITES
        │           ├─> MOSTRAR_ROADMAP
        │           ├─> FASE1_DOCS_BASE
        │           ├─> EVALUAR_PROTECCION_CIVIL
        │           ├─> FASE2_PREREQS (si aplica)
        │           ├─> FASE3_SIAPEM
        │           └─> CHECKLIST_FINAL
        ├─> FLUJO_TRAMITES_DIRECTO
        ├─> FLUJO_PROGRAMAS_APOYO
        └─> MIGRACION_SIAPEM
```

### 3.3 Flujo Detallado del Bot — Paso a Paso

#### Paso 0: Bienvenida (/start)

```
Bot: "¡Hola! Soy el Asesor Virtual de Viabilidad CDMX 🏙️
     Te ayudo a evaluar si tu negocio puede ser exitoso y
     qué trámites necesitas para abrirlo legalmente.
     
     ¿Qué quieres hacer?
     [🔍 Evaluar mi negocio]  [📋 Ver trámites]
     [💰 Programas de apoyo]"
```

#### Paso 1: Perfilamiento del Negocio

**1a. Giro comercial** — El bot pregunta con botones sugeridos:
```
Bot: "¿Qué tipo de negocio quieres abrir?
     [🍕 Restaurante]  [☕ Cafetería]  [🛒 Tienda]
     [💇 Estética]     [🏋️ Gimnasio]  [🍺 Bar/Cantina]
     [🏨 Hotel]        [✍️ Escribir otro]"
```
- Si el usuario escribe texto libre → Claude procesa con NLP y mapea al catálogo SCIAN/LEM.
- Si selecciona botón → mapeo directo.

**1b. Ubicación** — Tres niveles de precisión aceptados:
```
Bot: "¿Tienes una ubicación en mente?
     Puedes indicarme: Alcaldía, Colonia, o Dirección exacta."
```
- El bot acepta cualquiera de los tres y registra el nivel de precisión para el análisis.

**1c. Dimensiones y aforo** — Crítico para Protección Civil:
```
Bot: "Dos preguntas rápidas sobre el local:
     1️⃣ ¿El local tiene más de 250 m²? [Sí] [No] [No sé]
     2️⃣ ¿Esperas más de 100 personas al mismo tiempo? [Sí] [No] [No sé]"
```
- Si ambas son "No" → exento de Programa Interno de Protección Civil (Art. 10, Ap. A, Fr. X, LEM).
- Si cualquiera es "Sí" → obligatorio el Programa Interno de Protección Civil.
- Si "No sé" → bot asume el peor caso y lo indica.

**1d. Venta de alcohol** — Para clasificación LEM:
```
Bot: "¿Tu negocio incluye venta de alcohol?
     [No]  [Sí, como complemento a alimentos]  [Sí, como giro principal]"
```

#### Paso 2: Análisis de Viabilidad y Mercado

El bot cruza los datos del perfil con:

**2a. Competencia (DENUE):**
- Busca en el CSV de DENUE los establecimientos con el mismo SCIAN en la cuadra, colonia y alcaldía.
- Responde: "En la Colonia Roma hay 12 cafeterías registradas (DENUE 2024). En tu cuadra: 2."

**2b. Rentabilidad y gastos fijos estimados:**
- Usa venta mensual estimada, renta base por zona y gastos fijos declarados por el usuario.
- Genera indicadores 0-100 para rentabilidad y presión de gastos fijos.

**2c. Validación de Uso de Suelo:**
- Consulta CSV local de uso de suelo con compatibilidad giro-zona.
- **Regla crítica:** Si el giro es Impacto Zonal y la zona es Habitacional → bot detiene el flujo:
  ```
  Bot: "⚠️ Alerta: Un bar/cantina NO es compatible con uso de suelo
       Habitacional en esa ubicación (SEDUVI).
       Te recomiendo:
       [🔍 Buscar otra zona]  [🔄 Cambiar mi giro]  [📞 Consultar CENPROIN]"
  ```

**2d. Reporte de Viabilidad:**
```
Bot: "📊 REPORTE DE VIABILIDAD
     Negocio: Cafetería specialty
     Zona: Colonia Roma, Cuauhtémoc
     
     📍 Uso de suelo: Compatible (zona mixta)
     🏪 Competencia: 14 cafeterías en la colonia (moderada)
     💰 Rentabilidad estimada: margen sano
     🧾 Gastos fijos: presión moderada
     🔴 Riesgo: Diferenciarse con propuesta de valor única
     
     💡 Clasificación legal: Bajo Impacto (EM-03)
        → Trámite inmediato y gratuito en SIAPEM
     
     ¿Continúo con tu Roadmap de Trámites?
     [✅ Sí, quiero el roadmap]  [🔄 Cambiar datos]"
```

#### Paso 3: Clasificación del Impacto Legal

Basado en giro + respuesta sobre alcohol, el bot clasifica automáticamente:

| Condición | Impacto | Formato SIAPEM |
|-----------|---------|----------------|
| Cafetería/Tienda/Estética/Fonda sin alcohol | Bajo | EM-03 |
| Restaurante con alcohol, Gimnasio, Salón de Fiestas, Hotel | Vecinal | EM-11 |
| Bar/Cantina/Antro/Discoteca/Casino (alcohol como giro principal) | Zonal | EM-08 |

El bot confirma la clasificación al usuario y explica sus implicaciones antes de continuar.

#### Paso 4: Roadmap de Trámites (Fase 1 — Para todos)

```
Bot: "📋 HOJA DE RUTA — FASE 1 (Documentos base)
     Estos van antes de ir al SIAPEM:
     
     1️⃣ Cuenta Llave CDMX
        → Si no tienes, créala en: llave.cdmx.gob.mx
        ¿Ya tienes tu cuenta? [✅ Sí] [❌ No]
     
     2️⃣ Certificado Único de Zonificación (SEDUVI)
        → Vigencia máxima: 1 año
        → Confirma que tu giro está permitido en esa zona
        Tramitar en: [🔗 Enlace SEDUVI]
     
     3️⃣ Protección Civil
        → Resultado: ✅ EXENTO (local <100 personas y <250 m²)
        [o] → ⚠️ OBLIGATORIO: Programa Interno de Protección Civil"
```

#### Paso 5: Pre-requisitos por Impacto (Fase 2 — Solo Vecinal/Zonal)

```
Bot: "📋 FASE 2 — Documentos adicionales requeridos
     (Aplica porque tu negocio es Impacto [Vecinal/Zonal])
     
     🔴 Constancia de no adeudo de PREDIAL
        → Tesorería CDMX: [🔗 data.finanzas.cdmx.gob.mx/formato_lc]
     
     🔴 Constancia de no adeudo de AGUA (SACMEX)
        → Mismo enlace anterior
     
     Tip: Estos trámites pueden tomar 3-5 días hábiles."
```

#### Paso 6: Registro SIAPEM (Fase 3)

El bot guía paso a paso según el formato asignado:

**Para EM-03 (Bajo Impacto):**
```
Bot: "🏛️ SIAPEM — Aviso de Funcionamiento (EM-03)
     Ingresa a: siapem.cdmx.gob.mx
     
     1. Inicia sesión con tu Llave CDMX
     2. Mis negocios → Dar de alta nuevo negocio
     3. Tipo de persona: [Física] o [Moral]
     4. Alta información del negocio
     5. Mis trámites → Registrar nuevo trámite
     6. Seleccionar tu negocio
     7. Formato: EM-03 funcionamiento de bajo impacto
     8. Registrar la información
     9. Descargar Acuse e imprimir ✅
     
     Costo: $0 MXN | Tiempo: Inmediato
     ¿Necesitas ayuda con algún paso? [1][2][3][4][5][6][7][8][9]"
```

**Para EM-11 (Impacto Vecinal):**
- Mismos pasos 1-6, luego formato EM-11.
- Paso adicional: Pagar línea de captura (Art. 191, Fr. I, Código Fiscal CDMX).
- Descargar Acuse tras pago.
- Tiempo: 5-15 días hábiles.

**Para EM-08 (Impacto Zonal):**
- Mismos pasos 1-6, luego formato EM-08.
- **Diferencia crítica:** No es Aviso, es Solicitud de Permiso.
- Pago de derechos (Art. 191, Fr. II, Código Fiscal CDMX).
- **Esperar autorización expresa de la Alcaldía** (15-45 días).
- El bot informa activamente que este formato requiere aprobación, no es automático.

#### Paso 7: Checklist Final y Exportación

```
Bot: "✅ CHECKLIST COMPLETO — Tu Negocio CDMX
     
     □ Cuenta Llave CDMX
     □ Certificado de Zonificación SEDUVI (vigente 1 año)
     □ [Si aplica] Programa Interno Protección Civil
     □ [Vecinal/Zonal] Constancia No Adeudo Predial
     □ [Vecinal/Zonal] Constancia No Adeudo Agua
     □ Registro SIAPEM — Formato [EM-03/EM-11/EM-08]
     □ Pago de derechos [si aplica]
     □ [Solo Zonal] Esperar autorización Alcaldía
     
     💾 [Guardar en Mis Negocios]
     📄 [Exportar PDF] (próximamente)
     📞 ¿Dudas? CENPROIN: Av. Cuauhtémoc 899, Narvarte
        L-V 9:00-14:30 | dudas.siapem@sedeco.cdmx.gob.mx"
```

### 3.4 Flujo de Migración SIAPEM (Caso especial)

Cuando el usuario tiene trámites previos en la plataforma anterior:

```
Bot detecta: "¿Ya tramitaste antes con Clave Única?"
  → [Sí, tengo registro anterior]
  
Bot: "Para migrar al nuevo SIAPEM necesitas:
     1. PDF de tus trámites anteriores (EM-03/EM-B, EM-11/EM-A, EM-08)
     2. Certificado de Uso de Suelo original
     3. [Vecinal/Zonal] Constancias de no adeudo actualizadas
     
     Proceso en SIAPEM:
     → Mis negocios → 'Dar de alta un establecimiento 
       que ya cuenta con Clave Única'
     → NO des de alta un negocio nuevo"
```

### 3.5 Menú de Programas de Apoyo

Módulo separado con información de:
- FONDESO (Fondo para el Desarrollo Social)
- Programa "Impulso CDMX" (capital semilla hasta $150k MXN)
- Fondo PyME CDMX (impulso digital)
- Programa "Suelo Legal" (15% reducción predial primer año)
- Compras públicas y mercados locales SEDECO

### 3.6 Comandos del Bot

| Comando | Función |
|---------|---------|
| `/start` | Menú principal |
| `/nuevo` | Iniciar evaluación de nuevo negocio |
| `/tramites` | Ir directo al módulo de trámites |
| `/apoyo` | Programas de apoyo SEDECO |
| `/migrar` | Flujo de migración SIAPEM |
| `/contacto` | Datos CENPROIN y soporte |
| `/cancelar` | Cancelar flujo actual |

---

## 4. Área 2 — Dashboard Web (Radar CDMX)

### 4.1 Stack del Dashboard

- **Frontend:** HTML5 + Bootstrap 5.3 + Chart.js 4.4 + Bootstrap Icons
- **Paleta visual:** Vino (#8B1E3F) + Oro (#D4AF37) — identidad Gobierno CDMX
- **JS:** Vanilla JS (sin frameworks, para simplicidad demo)
- **Hosting:** GitHub Pages o Railway (mismo servidor que la API)

### 4.2 Módulos del Dashboard

El HTML prototipo (`index.html`) define los siguientes módulos ya implementados:

#### Módulo A: Filtros Interactivos (ya funcional)
- **Zona/Alcaldía:** Centro Histórico, Polanco, Condesa/Roma, Santa Fe, Coyoacán, Tlalpan
- **Giro del negocio:** Restaurante, Cafetería, Tienda de abarrotes, Farmacia, Gimnasio, Oficina
- **Inversión estimada (MXN):** Input numérico
- **Empleos a generar:** Input numérico
- Todos los cambios actualizan el dashboard automáticamente vía `actualizarDashboard()`

#### Módulo B: Métricas Principales (extra si hay tiempo)
- No es parte crítica del MVP.
- Si se implementa, debe mostrar únicamente métricas que alimentan el radar MVP: competencia, rentabilidad y gastos fijos.
- Evitar presentar un porcentaje de viabilidad general como si fuera score oficial mientras el score API quede pendiente.

#### Módulo C: Gráfica Radar — Factores Clave de Éxito (extra si hay tiempo)
Radar MVP de 3 variables: **Competencia**, **Rentabilidad** y **Gastos fijos**. Implementado con Chart.js tipo `radar` si el tiempo alcanza.

Quedan fuera del MVP: afluencia, capacidad de inversión, generación de empleos, apoyo legal y cualquier score compuesto expuesto como API.

#### Módulo D: Compatibilidad de Uso de Suelo (funcional, enriquecer)
- Muestra compatibilidad giro-zona basada en CSV local de uso de suelo.
- Botón "Validar ubicación exacta" → consulta local del CSV. La conexión a SEDUVI queda fuera del MVP.
- Mostrar artículo de LEM aplicable (Arts. 22-28).

#### Módulo E: Ruta de Trámites RETYS/SIAPEM (funcional con fuentes documentales)
Tabla con: Trámite, Ventanilla, Plazo estimado, Costo MXN, Requisitos clave.

Trámites incluidos:
| Trámite | Ventanilla | Plazo | Costo |
|---------|-----------|-------|-------|
| Aviso de Funcionamiento (EM-03/11/08) | SIAPEM Digital | Inmediato a 45 días | $0 a variable |
| Certificado Uso de Suelo (CUS) | SEDUVI | 5-15 días | $1,520 aprox |
| Protección Civil | PC CDMX | 10 días | $840 aprox |
| Registro de Marca (opcional) | IMPI | 30 días | $2,579 |

El módulo calcula **tiempo total estimado** y **costo total** dinámicamente según la clasificación del giro seleccionado.

#### Módulo F: Recomendaciones SEDECO Personalizadas (ya funcional)
- Se regeneran automáticamente al cambiar filtros.
- Incluye: competencia, programa de apoyo aplicable, status de uso de suelo.

#### Módulo G: Beneficios de Cumplir Normativa
- Clausura cero / operación 100% legal.
- Reducción 15% predial primer año (Programa Suelo Legal).
- Acceso a compras públicas y mercados locales.
- Botón CTA: "Asesoría en línea con especialista RETYS".

#### Módulo H: Contacto y CTA Final
- Telegram: @vIAbilibot (datos de demo).
- Botón directo: "Iniciar trámite en SIAPEM" → `window.open('https://siapem.cdmx.gob.mx')`.

### 4.3 Mejoras a implementar sobre el prototipo HTML

Las siguientes mejoras llevan el prototipo del estado demo al estado funcional:

1. **Reemplazar `zonasData` hardcodeado** por llamada a API backend con datos DENUE reales.
2. **Hacer dinámica la tabla de trámites** según el giro seleccionado (Bajo/Vecinal/Zonal cambia el formato SIAPEM, el costo y el plazo), usando fixtures/documentos locales.
3. **Añadir sección de Análisis de Competencia** con tabla de establecimientos similares en la zona (datos DENUE).
4. **Integrar mapa** (Leaflet.js o Google Maps embed) que muestre competidores en la zona seleccionada.
5. **Añadir panel de Programas de Apoyo** con filtrado por tipo de negocio y etapa del emprendimiento.
6. **Botón "Ir al Bot"** que abre el bot de Telegram con `/start` precargado.
7. **Hacer responsivo el dashboard** (el prototipo ya usa Bootstrap pero necesita prueba en móvil).
8. **Extra:** añadir sección de score detallado si hay tiempo, limitada a competencia, rentabilidad y gastos fijos.
9. **Barra de navegación sticky** ya implementada — verificar z-index y comportamiento en scroll.
10. **Footer con datos reales** de SEDECO y disclaimer legal.

---

## 5. Capa de IA y RAG

### 5.1 Motor de IA

**Elección primaria:** Claude 3.5 Sonnet (Anthropic)
**Alternativa:** GPT-4o (OpenAI)

Uso en el sistema:
- Interpretar texto libre del usuario y mapear al catálogo de giros.
- Generar respuestas conversacionales naturales en español.
- Responder preguntas sobre trámites específicos usando el contexto RAG.
- Generar el Reporte de Viabilidad narrativo.
- Detectar casos edge (usuario confundido, giro no reconocido, pregunta fuera de scope).

### 5.2 Sistema RAG (Retrieval-Augmented Generation)

**Documentos base para el vector store:**
1. Ley de Establecimientos Mercantiles CDMX 2025 (PDF)
2. Reglamento de la LEM (PDF)
3. Manuales CENPROIN: EM-03, EM-11, EM-08, Migración (ya documentados en `Manuales Cenproin.md`)
4. Catálogo de giros por SCIAN (`catalogos_giros.pdf`)
5. Guía SIAPEM (PDF de Google Drive)
6. Catálogo RETYS scrapeado (JSON)

**Implementación:**
```python
# Esquema básico del RAG
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.anthropic import Anthropic

documents = SimpleDirectoryReader("./data/documentos").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=Anthropic(model="claude-3-5-sonnet"))

# En el bot, cuando el usuario pregunta algo:
response = query_engine.query(user_question)
```

**ChromaDB como vector store persistente** para no re-indexar en cada reinicio.

### 5.3 Prompt del Sistema para el Bot

```
Eres el Asesor Virtual de Viabilidad CDMX, un asistente 
especializado en ayudar a emprendedores a evaluar si su 
negocio puede ser viable en la Ciudad de México y guiarlos 
en sus trámites legales.

Contexto legal:
- Ley de Establecimientos Mercantiles CDMX (2025)
- Tres categorías de impacto: Bajo (EM-03), Vecinal (EM-11), 
  Zonal (EM-08)
- Plataforma oficial: SIAPEM (siapem.cdmx.gob.mx)
- Certificado de uso de suelo: SEDUVI

Reglas:
1. Siempre confirma el giro y la ubicación antes de clasificar.
2. Si el uso de suelo es incompatible, detén el flujo y sugiere alternativas.
3. Distingue entre Aviso (Bajo/Vecinal) y Solicitud de Permiso (Zonal).
4. Para Impacto Zonal, enfatiza que requiere autorización expresa de la Alcaldía.
5. Proporciona siempre los enlaces oficiales.
6. Si no sabes algo, remite a CENPROIN: dudas.siapem@sedeco.cdmx.gob.mx

Responde siempre en español, de forma clara y amigable.
```

---

## 6. Base de Datos y Estado

### 6.1 Esquema SQLite

```sql
-- Sesiones de conversación del bot
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,           -- telegram_user_id
    state TEXT,                    -- estado actual del FSM
    data JSON,                     -- datos recopilados (giro, ubicación, etc.)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- No se crea tabla de negocios guardados en el MVP.
-- El bot conserva solo estado de conversación y resultados temporales.

-- Catálogo de giros (fixture)
CREATE TABLE giros (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    scian TEXT,
    impacto TEXT,
    formato_siapem TEXT,
    descripcion TEXT,
    keywords JSON                  -- para matching de texto libre
);

-- Datos de competencia por zona (fixture DENUE)
CREATE TABLE competencia (
    alcaldia TEXT,
    colonia TEXT,
    scian TEXT,
    total_establecimientos INTEGER,
    fuente TEXT DEFAULT 'DENUE-2024'
);

-- Log de interacciones para métricas
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    action TEXT,
    giro TEXT,
    zona TEXT,
    timestamp TIMESTAMP
);
```

### 6.2 JSON Fixtures de Datos Sintéticos

**`data/zonas.json`** — Datos de viabilidad por zona:
```json
{
  "Cuauhtémoc": {
    "colonias": {
      "Roma Norte": { "competencia_base": 70, "renta_m2": 575, "uso_suelo_mixto": true },
      "Condesa": { "competencia_base": 68, "renta_m2": 590, "uso_suelo_mixto": true },
      "Centro Histórico": { "competencia_base": 75, "renta_m2": 350, "uso_suelo_mixto": true }
    }
  },
  "Miguel Hidalgo": {
    "colonias": {
      "Polanco": { "competencia_base": 65, "renta_m2": 650, "uso_suelo_mixto": true },
      "Lomas de Chapultepec": { "competencia_base": 45, "renta_m2": 700, "uso_suelo_mixto": false }
    }
  }
}
```

**`data/giros.json`** — Mapeo de giros a LEM:
```json
[
  { "nombre": "Cafetería", "scian": "722515", "impacto": "bajo", "formato": "EM-03",
    "keywords": ["café", "cafetería", "coffee", "cappuccino", "espresso"] },
  { "nombre": "Restaurante sin alcohol", "scian": "722511", "impacto": "bajo", "formato": "EM-03",
    "keywords": ["fonda", "comida", "restaurante", "taquería", "cocina"] },
  { "nombre": "Restaurante con alcohol", "scian": "722511", "impacto": "vecinal", "formato": "EM-11",
    "keywords": ["restaurante bar", "cantina fondo", "mariscos"] },
  { "nombre": "Bar", "scian": "722410", "impacto": "zonal", "formato": "EM-08",
    "keywords": ["bar", "cantina", "antro", "discoteca", "cervecería", "chelería"] }
]
```

---

## 7. API Backend Compartido

### 7.1 Endpoints FastAPI

```
POST   /api/viabilidad          → Extra si hay tiempo. Recibe {giro, alcaldia, colonia, m2, aforo, alcohol}
                                  Devuelve impacto, formato_siapem, uso_suelo, competencia, rentabilidad, gastos_fijos y recomendaciones.
                                  No exponer score oficial en MVP.

GET    /api/giros               → Lista todos los giros con su clasificación LEM
GET    /api/giros/buscar?q=...  → Búsqueda fuzzy de giro por texto libre

GET    /api/tramites/{impacto}  → Devuelve la ruta de trámites para Bajo/Vecinal/Zonal desde fixtures/documentos locales
GET    /api/tramites/{formato}  → Detalle de EM-03, EM-11 o EM-08

GET    /api/zonas               → Lista de alcaldías y colonias con datos de viabilidad
GET    /api/competencia?scian=&alcaldia=&colonia=  → Datos DENUE de competencia

POST   /api/bot/webhook         → Webhook de Telegram (python-telegram-bot)

GET    /health                  → Health check
```

### 7.2 Formato de Respuesta — `/api/viabilidad`

```json
{
  "impacto": "bajo",
  "formato_siapem": "EM-03",
  "proteccion_civil_requerida": false,
  "uso_suelo": {
    "compatible": true,
    "tipo": "mixto",
    "nota": "Compatible con giro comercial según CSV local de uso de suelo"
  },
  "competencia": {
    "colonia": 12,
    "alcaldia": 187,
    "nivel": "moderado"
  },
  "rentabilidad": { "nivel": "media", "descripcion": "Margen estimado razonable para la zona" },
  "gastos_fijos": { "nivel": "alto", "renta_estimada": 46000 },
  "tramites": {
    "fase1": ["Llave CDMX", "Certificado Uso de Suelo SEDUVI"],
    "fase2": [],
    "fase3": { "formato": "EM-03", "costo": 0, "plazo_dias": 0, "enlace": "https://siapem.cdmx.gob.mx" }
  },
  "programas_apoyo": ["Impulso CDMX", "Fondo PyME CDMX"],
  "links": {
    "siapem": "https://siapem.cdmx.gob.mx",
    "seduvi_certificado": "http://certificadodigital.cdmx.gob.mx:8080/CertificadoDigital/certificado/solicitaCertificado",
    "uso_suelo_consulta": "CSV local del proyecto"
  }
}
```

---

## 8. Lógica de Negocio Central

### 8.1 Algoritmo de Clasificación de Impacto

```python
def clasificar_impacto(giro: str, vende_alcohol: str) -> dict:
    giro_data = buscar_giro(giro)  # Busca en catálogo + fuzzy match
    
    # Regla de alcohol: si menciona venta principal → Zonal
    if vende_alcohol == "principal":
        if giro_data["impacto"] in ["bajo", "vecinal"]:
            return {"impacto": "zonal", "formato": "EM-08", "nota": "Venta principal de alcohol → Impacto Zonal"}
    
    return {
        "impacto": giro_data["impacto"],
        "formato": giro_data["formato_siapem"],
        "articulo_lem": giro_data["articulo_lem"]
    }
```

### 8.2 Indicadores de Radar MVP

```python
def calcular_radar_mvp(competencia, margen_estimado, gastos_fijos, uso_suelo_compatible):
    if not uso_suelo_compatible:
        return {"bloqueante": True, "nivel": "INCOMPATIBLE"}
    
    return {
        "competencia": normalizar_competencia(competencia),      # menor competencia = mejor indicador
        "rentabilidad": normalizar_margen(margen_estimado),      # mayor margen = mejor indicador
        "gastos_fijos": normalizar_gastos(gastos_fijos),         # menor gasto fijo = mejor indicador
        "bloqueante": False
    }
```

El score compuesto de viabilidad queda como extra para el final si hay tiempo.

### 8.3 Validación de Uso de Suelo

```python
def validar_uso_suelo(giro_impacto: str, zona_tipo: str) -> dict:
    # Matriz de compatibilidad cargada desde CSV local de uso de suelo
    # zona_tipo: 'habitacional', 'mixto', 'comercial', 'industrial'
    compatibilidad = {
        "bajo":     {"habitacional": True,  "mixto": True,  "comercial": True},
        "vecinal":  {"habitacional": False, "mixto": True,  "comercial": True},
        "zonal":    {"habitacional": False, "mixto": False, "comercial": True}
    }
    compatible = compatibilidad[giro_impacto].get(zona_tipo, False)
    
    return {
        "compatible": compatible,
        "zona_tipo": zona_tipo,
        "accion": None if compatible else "Buscar zona comercial o cambiar giro"
    }
```

### 8.4 Evaluación de Protección Civil

```python
def evaluar_proteccion_civil(m2: int, aforo: int) -> dict:
    # Art. 10, Ap. A, Fr. X, LEM
    exento = (m2 <= 250) and (aforo < 100)
    return {
        "requerido": not exento,
        "fundamento": "Art. 10, Ap. A, Fr. X, Ley de Establecimientos Mercantiles CDMX",
        "accion": "Sin requisito adicional" if exento else "Tramitar Programa Interno de Protección Civil"
    }
```

---

## 9. Fases de Implementación

### Fase 0 — Setup y Fixtures (Día 1, primeras 4 horas)

1. Crear repositorio GitHub con estructura de proyecto.
2. Configurar entorno virtual Python 3.11, instalar dependencias.
3. Crear token de Bot en @BotFather (Telegram).
4. Obtener API Key Claude (Anthropic).
5. Descargar CSV DENUE CDMX de INEGI.
6. Incorporar CSV local de uso de suelo y validar columnas mínimas.
7. Construir JSON fixtures: giros.json, zonas.json, tramites.json.
8. Parsear y limpiar `catalogos_giros.pdf` para enriquecer fixture de giros.
9. Deploy inicial en Railway con variables de entorno.

### Fase 1 — Bot Núcleo Funcional (Día 1, horas 4-12)

1. Implementar FSM con `ConversationHandler` en python-telegram-bot.
2. Flujo completo: START → Perfilamiento (giro, ubicación, dimensiones, alcohol).
3. Lógica de clasificación de impacto (Bajo/Vecinal/Zonal).
4. Generación del Roadmap de trámites estático por clasificación.
5. Evaluación de Protección Civil (m2 + aforo).
6. Detectar caso de migración SIAPEM.
7. Comandos: `/start`, `/nuevo`, `/tramites`, `/cancelar`.
8. Pruebas en Telegram con casos: cafetería, restaurante con alcohol, bar, salón de fiestas.

### Fase 2 — IA y Análisis de Viabilidad (Día 1-2, horas 12-20)

1. Integrar Claude API para parsing de giro en texto libre.
2. Conectar datos DENUE para análisis de competencia real.
3. Calcular indicadores MVP: competencia, rentabilidad y gastos fijos.
4. Generar Reporte de Viabilidad narrativo con Claude.
5. Validación de uso de suelo con CSV local.
6. Añadir recomendaciones de programas de apoyo SEDECO.
7. Implementar comando `/apoyo` con menú de fondos disponibles.

### Fase 3 — RAG sobre Documentos Oficiales (Día 2, horas 20-28)

1. Indexar PDFs oficiales (LEM, Reglamento, Guía SIAPEM, Manuales CENPROIN).
2. Configurar ChromaDB como vector store persistente.
3. Integrar motor de preguntas y respuestas en el bot (cuando el usuario hace pregunta libre).
4. Pruebas de calidad de respuestas RAG con preguntas reales de trámites.
5. Fallback a CENPROIN cuando RAG no tiene suficiente confianza.

### Fase 4 — Dashboard Web (Día 2, horas 28-36)

1. Mantener dashboard HTML funcional con datos locales; conexión API queda como extra si hay tiempo.
2. Hacer dinámica la tabla de trámites según clasificación del giro.
3. Añadir tabla de competidores por zona (datos DENUE).
4. Extra si hay tiempo: integrar mapa básico con Leaflet.js mostrando competidores.
5. Añadir panel de programas de apoyo.
6. Botón "Consultar con el Bot" que abre Telegram.
7. Asegurar diseño responsivo.

### Fase 5 — Pulido, Métricas y Demo (Día 3)

1. Logging de interacciones para métricas de demo, sin guardar negocios del usuario.
2. Extras si hay tiempo: módulos B/C completos del dashboard y score detallado vía API.
3. Preparar 3-5 casos de demo representativos:
   - Cafetería en Condesa (Bajo Impacto, uso suelo compatible, demo rápida).
   - Restaurante con alcohol en Roma (Vecinal, requisitos adicionales).
   - Bar en colonia Habitacional (bloqueo por uso de suelo, sugerencia de reubicación).
   - Bar en zona comercial (Zonal, flujo completo con espera de Alcaldía).
   - Usuario con registro previo (migración SIAPEM).
4. Pruebas de stress y edge cases.
5. Preparar script de presentación de 5 minutos.

---

## 10. Stack Tecnológico Consolidado

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| **Bot Framework** | python-telegram-bot v22 | ConversationHandler nativo, soporte Telegram robusto |
| **API Backend** | FastAPI | Async, tipado, docs automáticas |
| **IA Principal** | Claude 3.5 Sonnet (Anthropic) | Mejor comprensión de español, razonamiento legal |
| **RAG** | LlamaIndex + ChromaDB | Indexación de PDFs oficiales |
| **Base de Datos** | SQLite (dev) → PostgreSQL (prod) | Simple para hackathon, escalable |
| **Dashboard Frontend** | HTML5 + Bootstrap 5.3 + Chart.js | Prototipo ya existente, sin build step |
| **Mapa** | Leaflet.js (CDN) | Open source, no requiere API key |
| **Deploy** | Railway | Deploy desde GitHub, variables de entorno, free tier |
| **Telegram Bot** | @vIAbilibot | Bot conversacional con python-telegram-bot |
| **PDF Processing** | pdfminer.six | Para extraer texto de PDFs CENPROIN/LEM |

---

## 11. Estructura de Archivos del Proyecto

```
vIAbleBOTCDMX/
├── index.html                    # Dashboard Web (ya existente, a enriquecer)
├── PLAN_IMPLEMENTACION.md        # Este documento
├── Documentos/                   # Fuentes documentales (ya existentes)
│   ├── Esquema_Flujo.md
│   ├── Flujo_Maestro_Asesoramiento.md
│   ├── Manuales Cenproin.md
│   ├── reporte_viableCDMX.md
│   ├── Problemas H.pdf
│   └── catalogos_giros.pdf
├── bot/
│   ├── main.py                   # Entry point del bot
│   ├── handlers/
│   │   ├── start.py              # /start y menú principal
│   │   ├── viabilidad.py         # Flujo de evaluación de viabilidad
│   │   ├── tramites.py           # Flujo de trámites paso a paso
│   │   ├── apoyo.py              # Programas de apoyo SEDECO
│   │   └── migracion.py          # Flujo de migración SIAPEM
│   ├── services/
│   │   ├── viabilidad_engine.py  # Lógica de clasificación y radar MVP
│   │   ├── tramites_service.py   # Generación de roadmaps
│   │   ├── denue_service.py      # Consulta de competencia DENUE
│   │   ├── suelo_service.py      # Validación uso de suelo desde CSV local
│   │   └── ai_service.py         # Integración Claude API + RAG
│   └── states.py                 # Constantes de estados FSM
├── api/
│   ├── main.py                   # FastAPI app
│   ├── routes/
│   │   ├── viabilidad.py
│   │   ├── giros.py
│   │   ├── tramites.py
│   │   ├── zonas.py
│   │   └── webhook.py            # Webhook Telegram
│   └── models.py                 # Pydantic models
├── data/
│   ├── giros.json                # Catálogo de giros + clasificación LEM
│   ├── zonas.json                # Datos base por zona
│   ├── uso_suelo.csv             # CSV local de compatibilidad de uso de suelo
│   ├── tramites.json             # Ruta de trámites por impacto
│   ├── programas_apoyo.json      # Fondos y programas SEDECO
│   └── denue_cdmx.csv            # CSV DENUE (descargar de INEGI)
├── rag/
│   ├── indexer.py                # Script para indexar PDFs
│   ├── documents/                # PDFs oficiales para RAG
│   │   ├── ley_establecimientos.pdf
│   │   ├── reglamento_lem.pdf
│   │   └── guia_siapem.pdf
│   └── chroma_db/                # Vector store persistente (gitignore)
├── db/
│   ├── database.py               # Conexión SQLite/PostgreSQL
│   ├── models.py                 # SQLAlchemy models
│   └── migrations/
├── tests/
│   ├── test_viabilidad.py
│   ├── test_tramites.py
│   └── test_clasificacion.py
├── requirements.txt
├── .env.example
├── Procfile                      # Para Railway
└── README.md
```

---

## 12. Detalles Técnicos por Módulo

### 12.1 Dependencias Python

```
# requirements.txt
python-telegram-bot==22.0
fastapi==0.111.0
uvicorn==0.30.0
anthropic==0.28.0
llama-index==0.10.0
llama-index-llms-anthropic==0.2.0
chromadb==0.5.0
sqlalchemy==2.0.30
pydantic==2.7.0
pdfminer.six==20221105
pandas==2.2.2
python-dotenv==1.0.1
httpx==0.27.0
fuzzywuzzy==0.18.0
python-Levenshtein==0.25.0
```

### 12.2 Variables de Entorno

```
# .env.example
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
DATABASE_URL=sqlite:///./viablecdmx.db
RAILWAY_ENVIRONMENT=development
WEBHOOK_URL=https://tu-app.railway.app
PORT=8000
```

### 12.3 ConversationHandler — Estructura FSM

```python
# bot/states.py
MENU, ASK_GIRO, ASK_UBICACION, ASK_M2, ASK_AFORO, ASK_ALCOHOL = range(6)
PROCESANDO, MOSTRAR_VIABILIDAD, CONFIRM_TRAMITES = range(6, 9)
FASE1, FASE2, FASE3_SIAPEM, CHECKLIST = range(9, 13)
MIGRACION, APOYO = range(13, 15)

# bot/main.py
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_handler)],
    states={
        MENU: [CallbackQueryHandler(menu_handler)],
        ASK_GIRO: [MessageHandler(filters.TEXT, giro_handler), CallbackQueryHandler(giro_btn_handler)],
        ASK_UBICACION: [MessageHandler(filters.TEXT, ubicacion_handler)],
        ASK_M2: [CallbackQueryHandler(m2_handler)],
        ASK_AFORO: [CallbackQueryHandler(aforo_handler)],
        ASK_ALCOHOL: [CallbackQueryHandler(alcohol_handler)],
        PROCESANDO: [CallbackQueryHandler(confirmar_viabilidad)],
        MOSTRAR_VIABILIDAD: [CallbackQueryHandler(viabilidad_handler)],
        FASE1: [CallbackQueryHandler(fase1_handler)],
        FASE2: [CallbackQueryHandler(fase2_handler)],
        FASE3_SIAPEM: [CallbackQueryHandler(siapem_handler)],
        CHECKLIST: [CallbackQueryHandler(checklist_handler)],
        MIGRACION: [CallbackQueryHandler(migracion_handler)],
        APOYO: [CallbackQueryHandler(apoyo_handler)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar_handler)],
    per_user=True,
    per_chat=True,
)
```

### 12.4 Dashboard — Mejoras JavaScript

Las siguientes funciones extienden el `actualizarDashboard()` ya existente:

```javascript
// Función para cargar datos reales desde API
async function cargarDatosAPI(zona, giro) {
    const resp = await fetch(`/api/viabilidad?zona=${zona}&giro=${giro}`);
    const data = await resp.json();
    return data;
}

// Función para renderizar tabla de trámites dinámica según impacto
function renderizarTramites(impacto) {
    const tramites = {
        'bajo': [
            { nombre: 'Certificado Uso de Suelo (SEDUVI)', plazo: '5-15 días', costo: '$1,520', req: 'Escrituras, croquis' },
            { nombre: 'Aviso de Funcionamiento EM-03 (SIAPEM)', plazo: 'Inmediato', costo: '$0', req: 'Llave CDMX, CUS, ID' }
        ],
        'vecinal': [/* ... */],
        'zonal': [/* ... */]
    };
    // Renderizar tabla HTML
}

// Integración Leaflet para mapa de competidores
function inicializarMapa(lat, lng, competidores) {
    const map = L.map('mapa').setView([lat, lng], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    competidores.forEach(c => L.marker([c.lat, c.lng]).addTo(map).bindPopup(c.nombre));
}
```

---

## 13. Casos Edge y Manejo de Errores

### 13.1 Casos especiales del Bot

| Caso | Manejo |
|------|--------|
| Giro no reconocido | Claude intenta clasificar; si falla, pide aclaración con ejemplos |
| Ubicación fuera de CDMX | Bot informa que el servicio es solo para CDMX y redirige |
| Uso de suelo incompatible | Detiene flujo, sugiere zona alternativa o cambio de giro |
| Giro Zonal en zona Habitacional | Bloqueo con explicación legal (Arts. 27 Bis LEM + SEDUVI) |
| Usuario con registro anterior SIAPEM | Detecta mención de "ya tenía" y ofrece flujo de Migración |
| Respuesta fuera de contexto | Recordatorio amistoso del scope y opción de reiniciar |
| API caída (SEDUVI/DENUE) | Fallback a datos de fixture + aviso al usuario |
| Timeout de Claude API | Respuesta de error amigable + reintento automático |

### 13.2 Mensajes de Error Amigables

```
Error de uso de suelo:
"⚠️ No pude verificar el uso de suelo en ese momento. 
Te recomiendo consultarlo directamente en:
🔗 ciudadmx.cdmx.gob.mx:8080/seduvi/
O contactar a CENPROIN: dudas.siapem@sedeco.cdmx.gob.mx"

Giro no encontrado:
"🤔 No pude identificar exactamente ese giro.
¿Tu negocio se parece a alguno de estos?
[Restaurante] [Cafetería] [Tienda] [Servicio profesional] [Otro]"
```

---

## 14. Canal de Comunicación

El bot está disponible en Telegram: **@vIAbilibot**.

---

## 15. Criterios de Aceptación y Demo

### 15.1 Criterios del Bot

- [ ] El bot responde a `/start` con menú funcional en Telegram.
- [ ] Flujo completo Bajo Impacto (cafetería) termina en checklist con links oficiales en <10 mensajes.
- [ ] Flujo Vecinal (restaurante con alcohol) incluye requisito de constancias de no adeudo.
- [ ] Flujo Zonal (bar) alerta sobre solicitud de permiso vs aviso y espera de Alcaldía.
- [ ] Giro incompatible con uso de suelo detiene el flujo y sugiere alternativas.
- [ ] Preguntas libres sobre trámites son respondidas por RAG con citas de la LEM.
- [ ] Migración SIAPEM fluye correctamente para usuarios con registro previo.

### 15.2 Criterios del Dashboard

- [ ] Dashboard carga en <3 segundos.
- [ ] Cambio de filtros actualiza todas las métricas en tiempo real.
- [ ] Radar chart refleja correctamente los 5 factores de viabilidad.
- [ ] Tabla de trámites cambia según el giro seleccionado (Bajo/Vecinal/Zonal).
- [ ] Botón SIAPEM abre la plataforma oficial en nueva pestaña.
- [ ] Dashboard es responsive en móvil.
- [ ] Score de viabilidad muestra estado VIABLE/CON RIESGO/NO RECOMENDADO según umbral.

### 15.3 Guión de Demo (5 minutos)

1. **Min 0:30** — Contexto: el problema de los emprendedores en CDMX (datos DENUE, LEM).
2. **Min 1:30** — Demo Bot Telegram: cafetería en Condesa → flujo completo → checklist EM-03.
3. **Min 3:00** — Demo Bot: bar en zona habitacional → bloqueo por uso de suelo → sugerencia alternativa.
4. **Min 4:00** — Demo Dashboard: mostrar Radar CDMX con Polanco + cafetería, cambiar a Santa Fe + gimnasio, mostrar cambio en métricas y trámites.
5. **Min 4:45** — Arquitectura técnica y roadmap (datos reales DENUE, integraciones SEDUVI API).

### 15.4 Datos de Contacto para Demo

- **CENPROIN:** Av. Cuauhtémoc 899, Col. Narvarte, Alcaldía Benito Juárez
- **Horario:** Lunes a viernes, 9:00 a 14:30 horas
- **Soporte SIAPEM:** dudas.siapem@sedeco.cdmx.gob.mx
- **SIAPEM:** https://siapem.cdmx.gob.mx
- **RETYS:** https://www.registrodetramitesyservicios.cdmx.gob.mx

---

*Documento generado a partir del cruce de: `Flujo_Maestro_Asesoramiento.md`, `Esquema_Flujo.md`, `Manuales Cenproin.md`, `reporte_viableCDMX.md`, `Problemas H.pdf` (Reto 2 — Hackathon NVIDIA/SEDECO) e `index.html` (prototipo Dashboard Radar CDMX).*
