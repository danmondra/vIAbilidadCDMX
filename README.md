# vIAble CDMX

**Asistente inteligente de viabilidad de negocios para la Ciudad de México**

[![Telegram](https://img.shields.io/badge/Telegram-@vIAbilibot-26A5E4?logo=telegram)](https://t.me/vIAbilibot)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Descripción

vIAble CDMX es un asistente virtual que ayuda a emprendedores a determinar si su negocio es viable en una ubicación específica de la Ciudad de México. El sistema analiza:

- **Clasificación legal** del giro según la Ley de Establecimientos Mercantiles (LEM)
- **Compatibilidad de uso de suelo** contra datos reales de SEDUVI
- **Competencia en la zona** usando datos reales del DENUE (INEGI)
- **Rentabilidad estimada** basada en rentas promedio y márgenes sectoriales
- **Ruta de trámites** personalizada con formatos SIAPEM (EM-03, EM-11, EM-08)
- **Programas de apoyo** gubernamentales disponibles (FONDESO, Impulso CDMX, etc.)

El proyecto fue desarrollado para el **Hackathon SEDECO + Saptiva AI — Reto 2: Viabilidad de Negocios CDMX**.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend API | Python 3.11+ / FastAPI |
| Bot | python-telegram-bot v22 (FSM / ConversationHandler) |
| Base de datos | SQLite 1.2M+ registros con SQLAlchemy 2.0 |
| IA | Anthropic Claude (`claude-sonnet-4-6`) |
| RAG | LlamaIndex + ChromaDB + HuggingFace `BAAI/bge-small-en-v1.5` |
| Frontend | HTML + Bootstrap 5 + Chart.js (Radar CDMX) |
| Fuzzy matching | fuzzywuzzy + python-Levenshtein |
| Despliegue | Railway / Uvicorn |

---

## Arquitectura

```
┌─────────────────────┐     ┌──────────────────────────────────────┐
│   Telegram Bot      │────▶│          FastAPI (api/)              │
│   (bot/)            │     │  /api/viabilidad  /api/giros         │
│                     │     │  /api/zonas       /api/tramites      │
│   FSM con estados   │     │  /api/bot/webhook                    │
│   ConversationHandler│    └──────────┬───────────────────────────┘
└─────────────────────┘               │
                                      ▼
┌──────────────────────────────────────────────────────────────┐
│                    Servicios (bot/services/)                  │
│  viabilidad_engine │ suelo_service │ denue_service           │
│  tramites_service  │ ai_service (Claude)                     │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              Base de datos SQLite (data/viabilidad.db)       │
│  giros │ competencia_denue │ uso_suelo │ zonas_renta        │
│  catalogo_cp │ tramites_pasos │ siapem_formatos             │
│  programas_apoyo │ legal_rules │ rentabilidad_sectores      │
└──────────────────────────────────────────────────────────────┘
```

---

## Requisitos

- Python 3.11 o superior
- Token de bot de Telegram (de [@BotFather](https://t.me/BotFather))
- API key de [Anthropic Claude](https://console.anthropic.com/)
- ~2 GB de espacio libre (base de datos + dependencias)

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/ericmt-98/vIAbleCDMX.git
cd vIAbleCDMX

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con TELEGRAM_BOT_TOKEN y ANTHROPIC_API_KEY

# 5. Poblar la base de datos
python db/seed.py

# 6. Iniciar el servidor
uvicorn api.main:app --reload --port 8000
```

---

## Variables de entorno

| Variable | Descripción | Obligatorio |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | Sí |
| `ANTHROPIC_API_KEY` | API key de Anthropic Claude | Sí |
| `DATABASE_URL` | URL de base de datos (default: SQLite local) | No |
| `WEBHOOK_URL` | URL pública para webhook (producción) | No |
| `PORT` | Puerto del servidor (default: 8000) | No |

---

## Uso: Bot de Telegram

1. Inicia una conversación con [@vIAbilibot](https://t.me/vIAbilibot)
2. Presiona **🔍 Evaluar mi negocio**
3. Selecciona o escribe el tipo de negocio (ej: "Restaurante", "Taquería")
4. Indica la ubicación (colonia y alcaldía)
5. Responde la superficie, aforo y venta de alcohol
6. Recibe un reporte completo de viabilidad con:
   - Clasificación según LEM
   - Compatibilidad de uso de suelo
   - Análisis de competencia con datos reales DENUE
   - Radar MVP (competencia, rentabilidad, gastos fijos)
   - Roadmap personalizado de trámites SIAPEM

### Flujo del bot

```
/start → Menú principal
         ├── 🔍 Evaluar mi negocio (perfilamiento → análisis → roadmap)
         ├── 📋 Ver trámites directos
         ├── 💰 Programas de apoyo
         └── 🔄 Migrar registro SIAPEM
```

### Análisis de viabilidad (flujo detallado)

```
Inicio → ¿Qué tipo de negocio? → ¿Ubicación? → ¿Superficie? →
¿Aforo? → ¿Vende alcohol? → Procesando... →
┌─ Reporte de viabilidad ──────────────────────────┐
│ 📊 CLASIFICACIÓN LEGAL (LEM)                     │
│    • Impacto: BAJO / VECINAL / ZONAL             │
│    • Formato SIAPEM: EM-03 / EM-11 / EM-08       │
│ 🗺️ USO DE SUELO                                  │
│    • Compatibilidad con la zona                  │
│ 🛡️ PROTECCIÓN CIVIL                              │
│    • Requerido / Exento                          │
│ 📈 ANÁLISIS DE MERCADO                           │
│    • Ventaja competitiva (vs DENUE)              │
│    • Rentabilidad estimada                       │
│    • Nivel de gastos fijos                       │
└──────────────────────────────────────────────────┘
        ↓
   ¿Continuar con Roadmap de Trámites?
        ↓
   Fase 1: Documentos Base (Llave CDMX + CUS SEDUVI + PC)
   Fase 2: Pre-requisitos especiales (si aplica)
   Fase 3: Registro SIAPEM
   ✅ Checklist final
```

---

## API REST

### Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/giros` | Lista todos los giros |
| GET | `/api/giros/buscar?q=` | Búsqueda difusa de giros |
| POST | `/api/viabilidad` | Análisis completo de viabilidad |
| GET | `/api/zonas` | Lista alcaldías y colonias |
| GET | `/api/competencia?scian=&alcaldia=` | Datos de competencia |
| GET | `/api/tramites/{impacto}` | Trámites por nivel de impacto |
| GET | `/api/tramites/formato/{formato}` | Instrucciones de formato SIAPEM |

### Ejemplo: POST /api/viabilidad

```json
{
  "giro": "Restaurante",
  "alcaldia": "Cuauhtémoc",
  "colonia": "Roma Norte",
  "m2": 120,
  "aforo": 60,
  "alcohol": "complemento"
}
```

**Respuesta:** Análisis completo con clasificación legal, uso de suelo, competencia, rentabilidad, gastos fijos, ruta de trámites y programas de apoyo.

---

## Dashboard Web (Radar CDMX)

El proyecto incluye un dashboard web en `index.html` que se sirve desde la misma API. Abre `http://localhost:8000` para acceder.

Características:
- Selección de giro, alcaldía y colonia desde catálogos en vivo
- Gráfica radar MVP (competencia, rentabilidad, gastos fijos)
- Tabla de trámites obligatorios
- Recomendaciones personalizadas
- Integración con el bot de Telegram

---

## Decisiones técnicas

- **FSM nativo (python-telegram-bot)** en lugar de frameworks externos, para mantener el control total del flujo
- **SQLite** como base de datos por su simplicidad de despliegue; la capa SQLAlchemy permite migrar a PostgreSQL sin cambios en la lógica
- **Fuzzywuzzy** como respaldo a Claude para clasificación de giros, asegurando funcionamiento incluso sin API key
- **Claude** para clasificación de texto libre y Q&A sobre trámites, con system prompt que codifica la LEM CDMX
- **Datos reales**: competencia DENUE (462K+ registros), uso de suelo SEDUVI (1.2M+ registros), rentas por zona

---

## Estructura del proyecto

```
├── api/              # FastAPI — endpoints REST
│   ├── main.py
│   ├── models.py
│   └── routes/
├── bot/              # Telegram bot
│   ├── main.py
│   ├── states.py
│   ├── handlers/
│   └── services/
├── db/               # Capa de base de datos
│   ├── database.py
│   ├── models.py
│   └── seed.py
├── data/             # Base de datos SQLite (~1.2M registros)
├── rag/              # RAG pipeline (LlamaIndex + ChromaDB)
├── Documentos/       # Documentación de referencia
├── index.html        # Dashboard web
├── Procfile          # Configuración de despliegue
└── requirements.txt  # Dependencias Python
```

---

## Licencia

MIT License — ver [LICENSE](LICENSE) para detalles.

---

## Contacto

**Secretaría de Desarrollo Económico (SEDECO) CDMX**

- Centro Promotor de Inversión (CENPROIN)
- 📍 Av. Cuauhtémoc 899, Col. Narvarte, Alcaldía Benito Juárez
- 🕐 Lunes a viernes, 9:00 a 14:30 horas
- 📧 dudas.siapem@sedeco.cdmx.gob.mx
- 🌐 siapem.cdmx.gob.mx

---

*Proyecto para el Hackathon SEDECO + Saptiva AI — 6 de junio de 2026*
