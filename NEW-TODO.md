# vIAbleCDMX — Migración completa a `data/viabilidad.db`

Este documento es el plan de ejecución para el siguiente agente. La meta es eliminar **toda** la información hardcoded y todo el consumo de JSON legacy. Tanto la API como el bot de Telegram deben depender exclusivamente de la base de datos consolidada `data/viabilidad.db`.

**NO INVENTAR NI HARDCODEAR DATOS. Si falta información, preguntar al usuario.**

---

## 0. Contexto del estado actual

### Base de datos consolidada (ya existe en `data/viabilidad.db`)
| Tabla | Filas | Contenido |
|---|---|---|
| `giros` | 577 | `clave_scian`, `descripción`, `horario_de_operación`, `tipo_de_impacto` |
| `competencia_denue` | 462,732 | `scian`, `colonia`, `codigo_postal`, `alcaldia` (DENUE real) |
| `uso_suelo` | 1,216,028 | `codigo_postal`, `uso_descripcion` (SEDUVI real) |
| `catalogo_cp` | 2,134 | `codigo_postal` → `colonia`, `alcaldia` |
| `zonas_renta` | 1,286 | `codigo_postal` → `renta_m2` |
| `rentabilidad_sectores` | 578 | `scian_prefix` → `margen_operativo` (de EMS INEGI) |
| `sessions` | 0 | autogenerada (vacía) |
| `interactions` | 0 | autogenerada (vacía) |

### DB vacía que se debe eliminar
- `viablecdmx.db` (raíz) — autogenerada por SQLAlchemy, 0 filas. Se elimina y se consolida todo en `data/viabilidad.db`.

### Archivos que actualmente consumen datos hardcoded / JSON legacy
- `api/routes/giros.py` → lee `data/giros.json`
- `api/routes/zonas.py` → lee `data/zonas.json`
- `api/routes/viabilidad.py` → lee `data/giros.json`, `data/zonas.json`, `data/tramites.json`
- `api/routes/tramites.py` → lee `data/tramites.json` + dict hardcoded de EM-03/EM-11/EM-08
- `bot/services/viabilidad_engine.py` → JSON + heurísticas hardcoded de ticket/visitas/margen
- `bot/services/suelo_service.py` → JSON + `ALCALDIAS_CDMX` hardcoded + matriz hardcoded
- `bot/services/denue_service.py` → JSON + CSV fallback
- `bot/services/tramites_service.py` → JSON + instrucciones hardcoded de EM-03/EM-11/EM-08
- `bot/services/ai_service.py` → JSON + lista hardcoded
- `bot/handlers/viabilidad.py` → `ALCALDIAS_CDMX`, `ALCALDIAS_NORMALIZADAS`, botones de giro hardcoded
- `bot/handlers/apoyo.py` → JSON + fallback hardcoded
- `index.html` → objeto `zonasData` hardcoded, `Math.random()` para tiempos/costos
- `db/database.py` → apunta a `viablecdmx.db` (la vacía)

### Archivos JSON/CSV a eliminar al final
- `data/giros.json`
- `data/zonas.json`
- `data/tramites.json`
- `data/programas_apoyo.json`
- `data/denue_sample.json`
- `data/uso_suelo.csv`

---

## 1. Crear `db/seed.py` (sqlite3 stdlib, sin HTTP, sin ORM)

Script idempotente que:
- Lee `data/giros.json` y hace `ALTER TABLE giros` + `UPDATE` para añadir `articulo_lem`, `formato_siapem`, `keywords` (JSON), `nombre_corto`.
- Lee `data/tramites.json` y crea `tramites_pasos` (con `fase` literal: `fase0`/`fase1`/`fase2`/`fase3`) + `siapem_formatos`.
- Lee `data/programas_apoyo.json` y crea `programas_apoyo`.
- Crea `legal_rules` con las 4 reglas del Plan §5 (ruido Art. 10 LEM, escuelas 300m Art. 27 Bis LEM, seguro RC, horarios máximos).
- Crea vista `v_giro_completo` uniendo `giros` con `rentabilidad_sectores`.

### Esquema nuevo (DDL)

```sql
-- Nuevas columnas en giros
ALTER TABLE giros ADD COLUMN articulo_lem TEXT;
ALTER TABLE giros ADD COLUMN formato_siapem TEXT;
ALTER TABLE giros ADD COLUMN keywords TEXT;        -- JSON array
ALTER TABLE giros ADD COLUMN nombre_corto TEXT;

-- Trámites desnormalizados (fase LITERAL como pidió el usuario)
CREATE TABLE IF NOT EXISTS tramites_pasos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  impacto TEXT NOT NULL,           -- bajo / vecinal / zonal
  fase TEXT NOT NULL,              -- fase0 / fase1 / fase2 / fase3
  paso INTEGER,
  nombre TEXT,
  descripcion TEXT,
  link TEXT,
  link_info TEXT,
  costo TEXT,
  plazo TEXT,
  obligatorio TEXT,                -- true / false / condicional
  condicion TEXT,                  -- e.g. "aforo >= 100 OR m2 > 250"
  fundamento TEXT,                 -- e.g. "Art. 10, Ap. A, Fr. X, LEM"
  orden INTEGER
);

-- Detalles SIAPEM
CREATE TABLE IF NOT EXISTS siapem_formatos (
  formato TEXT PRIMARY KEY,        -- EM-03 / EM-11 / EM-08
  impacto TEXT,
  tipo TEXT,                       -- "Aviso de Funcionamiento" / "Solicitud de Permiso"
  titulo TEXT,
  costo TEXT,
  plazo TEXT,
  pasos_json TEXT,                 -- array
  documentos_json TEXT,            -- array
  nota TEXT,
  advertencia TEXT,
  link TEXT
);

-- Programas de apoyo
CREATE TABLE IF NOT EXISTS programas_apoyo (
  id INTEGER PRIMARY KEY,
  nombre TEXT,
  organismo TEXT,
  descripcion TEXT,
  monto_max REAL,
  tipo TEXT,
  modalidad TEXT,
  tasa_interes TEXT,
  plazo_max_meses INTEGER,
  requisitos_json TEXT,
  link TEXT,
  aplica_giros_json TEXT,
  convocatoria TEXT,
  direccion TEXT,
  contacto TEXT,
  beneficios_adicionales_json TEXT,
  descuento TEXT,
  costo_renta TEXT,
  proyectos_elegibles_json TEXT,
  duracion_programa TEXT
);

-- Reglas legales (Plan §5)
CREATE TABLE IF NOT EXISTS legal_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  regla TEXT,                      -- ruido / escuela_300m / seguro_rc / horario_max
  fundamento TEXT,                 -- Art. 10 LEM, Art. 27 Bis LEM, etc.
  descripcion TEXT,
  aplica_impacto TEXT,             -- bajo / vecinal / zonal / todos
  aplica_giros_pattern TEXT,       -- regex sobre scian
  nivel_db INTEGER,                -- 85 / 75 / 300
  obligatorio INTEGER,             -- 0/1
  mensaje_usuario TEXT
);

-- Vista para joins frecuentes
CREATE VIEW IF NOT EXISTS v_giro_completo AS
SELECT g.no, g.clave_scian, g.descripción, g.tipo_de_impacto,
       g.horario_de_operación, g.articulo_lem, g.formato_siapem,
       g.keywords, g.nombre_corto,
       r.margen_operativo
FROM giros g
LEFT JOIN rentabilidad_sectores r ON g.clave_scian = r.scian_prefix;
```

### Lógica del seed
- Usar `sqlite3.connect("./data/viabilidad.db")` y ejecutar DDL con `IF NOT EXISTS` o `try/except` para columnas duplicadas.
- Hacer `INSERT OR REPLACE` para idempotencia.
- Cargar JSON con `json.load(open(path, encoding="utf-8"))`.
- Para `tramites.json`: iterar `bajo/vecinal/zonal` → `fase0/fase1/fase2` → cada `paso` con sus campos. La `fase3` se carga aparte en `siapem_formatos` (no en `tramites_pasos`).
- Para `legal_rules`: insertar manualmente las 4 reglas (datos del Plan §5 — Art. 10 LEM ruido 85/75 dB, Art. 27 Bis 300m escuelas, seguro responsabilidad civil, horarios por impacto).

### Datos a insertar en `legal_rules`

```python
LEGAL_RULES = [
    {
        "regla": "ruido",
        "fundamento": "Art. 10 LEM",
        "descripcion": "Aislantes acústicos si se superan 85 dB de día o 75 dB de noche",
        "aplica_impacto": "todos",
        "nivel_db": 85,  # día
        "obligatorio": 1,
        "mensaje_usuario": "Si tu negocio genera ruido considerable, deberás instalar aislantes acústicos..."
    },
    {
        "regla": "escuela_300m",
        "fundamento": "Art. 27 Bis LEM",
        "descripcion": "Prohibido instalar giros de impacto zonal a menos de 300m de escuelas",
        "aplica_impacto": "zonal",
        "nivel_db": 300,  # metros
        "obligatorio": 1,
        "mensaje_usuario": "Para giros de impacto zonal (bares, antros, casinos), se prohíbe su instalación a menos de 300m de una escuela"
    },
    {
        "regla": "seguro_rc",
        "fundamento": "Art. 10 LEM",
        "descripcion": "Póliza de responsabilidad civil obligatoria",
        "aplica_impacto": "todos",
        "obligatorio": 1,
        "mensaje_usuario": "Deberás contratar una póliza de seguro de responsabilidad civil antes de la apertura"
    },
    {
        "regla": "horario_max",
        "fundamento": "LEM CDMX",
        "descripcion": "Horarios máximos de operación según giro (bajo impacto, vecinal, zonal)",
        "aplica_impacto": "todos",
        "obligatorio": 1,
        "mensaje_usuario": "Tu giro tiene un horario máximo de operación según la ley"
    }
]
```

### Cómo correrlo
```bash
python db/seed.py
```

---

## 2. Consolidar la base de datos

### Cambios en `db/database.py`
```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/viabilidad.db")
```

### Borrar `viablecdmx.db`
```bash
rm viablecdmx.db
```

### Validar seed
```bash
sqlite3 data/viabilidad.db "SELECT COUNT(*) FROM tramites_pasos;"
sqlite3 data/viabilidad.db "SELECT COUNT(*) FROM siapem_formatos;"
sqlite3 data/viabilidad.db "SELECT COUNT(*) FROM programas_apoyo;"
sqlite3 data/viabilidad.db "SELECT COUNT(*) FROM legal_rules;"
sqlite3 data/viabilidad.db "SELECT nombre_corto, formato_siapem, articulo_lem FROM giros WHERE nombre_corto IS NOT NULL LIMIT 5;"
```

---

## 3. Refactorizar `api/routes/`

### `api/routes/giros.py`
- Quitar `load_giros()` y la dependencia de `data/giros.json`.
- Conectar a `db/database.py` con SQLAlchemy.
- `GET /api/giros` → `SELECT * FROM v_giro_completo` (paginado opcional).
- `GET /api/giros/buscar?q=...` → fuzzy match sobre `descripción` y `keywords` (cargar `keywords` como JSON y buscar coincidencias).

### `api/routes/zonas.py`
- Quitar `load_zonas()` y `competencia_por_scian` hardcoded.
- `GET /api/zonas` → `SELECT DISTINCT alcaldia, colonia FROM catalogo_cp ORDER BY alcaldia, colonia`.
- `GET /api/competencia?scian=...&alcaldia=...&colonia=...`:
  - Resolver `codigo_postal` desde `catalogo_cp` (filtro colonia/alcaldia).
  - `SELECT COUNT(*) FROM competencia_denue WHERE scian LIKE ? AND codigo_postal = ?`.
  - `SELECT renta_m2 FROM zonas_renta WHERE codigo_postal = ?`.
  - `SELECT uso_descripcion FROM uso_suelo WHERE codigo_postal = ?` (tomar la moda).

### `api/routes/viabilidad.py`
- Quitar todas las heurísticas hardcoded:
  - `_calc_rentabilidad`: leer `rentabilidad_sectores.margen_operativo` por prefijo SCIAN de 6 dígitos.
  - `_calc_gastos_fijos`: leer `zonas_renta.renta_m2` y calcular `renta = renta_m2 * m2` en backend.
  - `_calc_competencia`: `COUNT(*) FROM competencia_denue`.
  - `_calc_tramites`: unir `tramites_pasos` ordenado por `fase, orden`.
  - `_calc_uso_suelo`: leer `uso_suelo.uso_descripcion` y aplicar la matriz de compatibilidad (esta SÍ es lógica, no dato hardcoded).
- `POST /api/viabilidad` orquesta todo.

### `api/routes/tramites.py`
- `GET /api/tramites/{impacto}` → `SELECT * FROM tramites_pasos WHERE impacto=? ORDER BY fase, orden`.
- `GET /api/tramites/formato/{formato}` → `SELECT * FROM siapem_formatos WHERE formato=?` + `SELECT * FROM tramites_pasos WHERE impacto=? AND fase IN ('fase1','fase2')`.

### `api/routes/webhook.py`
- Sin cambios (solo reenvía al bot).

---

## 4. Refactorizar `bot/services/`

### `bot/services/viabilidad_engine.py`
- Reemplazar `_cargar_giros()` con query a `giros` table.
- `clasificar_impacto(giro_nombre, alcohol)`:
  - Cargar `SELECT clave_scian, descripción, tipo_de_impacto, keywords, nombre_corto, horario_de_operación FROM v_giro_completo`.
  - Fuzzy match sobre `descripción` + `keywords`.
  - Regla de alcohol: si `alcohol == "principal"` → forzar `zonal` y `EM-08`, `Art. 27 Bis LEM (Alcohol Principal)`.
  - Devolver `impacto`, `formato_siapem`, `articulo_lem`, `giro_nombre`, `scian`, `horario_operación` (este último desde `giros.horario_de_operación`).
- `validar_uso_suelo(impacto, zona_tipo)`: igual que ahora (es lógica normativa, no dato).
- `calcular_radar_mvp(...)`:
  - `competencia_score`: igual lógica de inversión.
  - `rentabilidad`: leer `rentabilidad_sectores.margen_operativo` por prefijo SCIAN.
  - `gastos_fijos`: leer `zonas_renta.renta_m2` para el CP del usuario.
  - Quitar todos los defaults hardcoded (220, 100, 200, etc.) — leer siempre de DB.
- `evaluar_proteccion_civil`: igual (es lógica LEM, no dato).
- `generar_reporte_viabilidad`: añadir al reporte el `horario_operación` desde `giros`.

### `bot/services/suelo_service.py`
- Quitar `ALCALDIAS_CDMX` hardcoded y `_cargar_zonas()`.
- `_normalizar_alcaldia`: usar `SELECT DISTINCT alcaldia FROM catalogo_cp` para construir el mapa de normalización dinámicamente.
- `_obtener_zona_tipo`:
  - Buscar CP en `catalogo_cp` donde coincidan colonia + alcaldía.
  - Leer `uso_suelo.uso_descripcion` para ese CP (tomar la moda).
  - Leer `zonas_renta.renta_m2` para ese CP.
- Inferir `zona_tipo` desde `uso_descripcion`:
  - Contiene "Habitacional" sin "Comercio"/"Servicios" → `habitacional`
  - Contiene "Comercio" / "Centro de Barrio" / "Servicios" / "Mixto" → `mixto`
  - Contiene "Industria" / "Equipamiento" → `comercial`
  - (Codificar esto como función pura, no como dato.)

### `bot/services/denue_service.py`
- Eliminar `_buscar_en_csv` y `_buscar_en_zonas_json`.
- `buscar_competencia(scian, alcaldia, colonia)`:
  - Resolver CP desde `catalogo_cp` (preferir match exacto colonia+alcaldía, fallback alcaldía).
  - `SELECT COUNT(*) FROM competencia_denue WHERE scian LIKE ? AND codigo_postal = ?` (prefijo 4 dígitos para más resultados).
  - Para alcaldía: `SELECT COUNT(*) FROM competencia_denue WHERE scian LIKE ? AND alcaldia = ?`.
  - Nivel: `baja` ≤ 3, `moderada` 4-7, `alta` ≥ 8.

### `bot/services/tramites_service.py`
- Quitar `_cargar_tramites()` y `_tramites_fallback()`.
- `generar_roadmap(impacto, proteccion_civil)`:
  - `SELECT * FROM tramites_pasos WHERE impacto=? ORDER BY fase, orden`.
  - Para fase1/proteccion_civil, marcar como exento si `not proteccion_civil`.
  - Para fase3, leer de `siapem_formatos`.
- `formatear_checklist(impacto, proteccion_civil)`: leer pasos de DB y formatear.
- `get_formato_siapem_instrucciones(formato)`: leer de `siapem_formatos` y deserializar `pasos_json` / `documentos_json`.

### `bot/services/ai_service.py`
- `_cargar_lista_giros`: `SELECT DISTINCT nombre_corto, descripción FROM giros WHERE nombre_corto IS NOT NULL`.
- Quitar lista hardcoded fallback.
- `responder_pregunta_tramite`: el `system_context` puede quedarse (es texto legal estático, no dato variable). Solo actualizar para mencionar que los datos se consultan de la DB.

### `bot/handlers/viabilidad.py`
- Quitar `ALCALDIAS_CDMX` y `ALCALDIAS_NORMALIZADAS` (cargar dinámicamente de `catalogo_cp`).
- Quitar botones hardcoded de giro en `ask_giro_handler`:
  - Cargar top 8 giros más relevantes de la DB (ej. los primeros por `no`).
  - Añadir botón "✍️ Escribir otro...".
- `ubicacion_handler` ya no necesita `_parsear_ubicacion` con alcaldías hardcoded; usar `catalogo_cp` para fuzzy match.

### `bot/handlers/apoyo.py`
- Quitar fallback hardcoded.
- `SELECT * FROM programas_apoyo ORDER BY id`.

### `bot/handlers/start.py` y `migracion.py`
- Sin cambios estructurales (textos legales estáticos).

---

## 5. Refactorizar `index.html`

### Eliminar
- El objeto `zonasData` con Polanco/Condesa/Centro hardcoded.
- El select de giros hardcoded (línea 295-301).
- `Math.random()` para `tiempoTotal` y `costoTotal` (línea 541-542).
- Tabla de trámites con costos/plazos hardcoded (línea 405-411).

### Añadir
- `fetch('/api/zonas')` para poblar dinámicamente los selects de alcaldía y colonia.
- `fetch('/api/giros/buscar?q=...')` para el select de giro.
- `fetch('/api/viabilidad', {method:'POST', body: JSON.stringify({giro, alcaldia, colonia, m2, aforo, alcohol})})` para calcular.
- Pintar métricas reales: `viabilidadPorcentaje`, `competenciaVal`, `rentaEstimada` desde la respuesta.
- Pintar `costoTotal` y `tiempoTotal` desde `tramites.fase1+fase2+fase3.plazo` parseado.
- Pintar recomendaciones desde `uso_suelo.advertencia`, `competencia.recomendacion`, etc.
- Tabla de trámites renderizada con `tramites.fase1_pasos + fase2_pasos + fase3`.

---

## 6. Verificación manual

### API
```bash
# Encender la API
uvicorn api.main:app --reload

# Probar endpoints
curl http://localhost:8000/api/giros | jq '.[:3]'
curl "http://localhost:8000/api/giros/buscar?q=cafeteria" | jq
curl http://localhost:8000/api/zonas | jq '[:5]'
curl "http://localhost:8000/api/competencia?scian=722515&alcaldia=Cuauhtemoc&colonia=Roma%20Norte" | jq
curl -X POST http://localhost:8000/api/viabilidad \
  -H "Content-Type: application/json" \
  -d '{"giro":"Cafetería","alcaldia":"Cuauhtémoc","colonia":"Roma Norte","m2":120,"aforo":40,"alcohol":"no"}' | jq
```

### Bot
```bash
python bot/main.py
# En Telegram: /start → Evaluar mi negocio → Cafetería → Roma Norte, Cuauhtémoc → flujo completo
```

### Frontend
Abrir `index.html` en el navegador (con la API corriendo) y verificar que los selects y métricas cargan datos reales.

---

## 7. Eliminar archivos legacy

Solo después de verificar que todo funciona:

```bash
rm data/giros.json
rm data/zonas.json
rm data/tramites.json
rm data/programas_apoyo.json
rm data/denue_sample.json
rm data/uso_suelo.csv
rm viablecdmx.db
```

---

## 8. Reglas para el agente ejecutor

1. **NO hardcodear datos.** Si un dato no existe en la DB, pregunta al usuario antes de inventarlo.
2. **No eliminar archivos hasta verificar** que la API + bot + frontend funcionan con la DB.
3. **El seed debe ser idempotente** (re-ejecutable sin duplicar).
4. **Verificar el orden de las fases** — primero el seed, luego la consolidación de DB, luego refactor de capas (api → bot services → bot handlers → frontend → limpieza).
5. **Si una columna de la DB no existe**, agregarla con `ALTER TABLE ... ADD COLUMN` y manejar NULL en queries.
6. **Los textos legales estáticos** (mensajes de error, copy de CENPROIN, horarios genéricos) SÍ pueden quedarse en código. Lo que se mueve a DB son **datos variables** (giros, zonas, programas, márgenes, rentas, conteos DENUE).
7. **Las reglas LEM** (matriz de compatibilidad impacto × zona, condición de Protección Civil, escalado de alcohol) son **lógica de negocio**, no datos. Permanecen en código.

---

## 9. Estructura de archivos final esperada

```
vIAbleCDMX/
├── api/
│   ├── main.py
│   ├── models.py
│   └── routes/
│       ├── giros.py          # REFACTORIZADO
│       ├── zonas.py          # REFACTORIZADO
│       ├── viabilidad.py     # REFACTORIZADO
│       ├── tramites.py       # REFACTORIZADO
│       └── webhook.py        # sin cambios
├── bot/
│   ├── main.py
│   ├── states.py
│   ├── handlers/
│   │   ├── start.py          # sin cambios
│   │   ├── viabilidad.py     # REFACTORIZADO
│   │   ├── tramites.py       # sin cambios (delegan a tramites_service)
│   │   ├── apoyo.py          # REFACTORIZADO
│   │   └── migracion.py      # sin cambios
│   └── services/
│       ├── ai_service.py     # REFACTORIZADO
│       ├── denue_service.py  # REFACTORIZADO
│       ├── suelo_service.py  # REFACTORIZADO
│       ├── tramites_service.py # REFACTORIZADO
│       └── viabilidad_engine.py # REFACTORIZADO
├── db/
│   ├── database.py           # MODIFICADO (apunta a data/viabilidad.db)
│   ├── models.py             # sin cambios
│   └── seed.py               # NUEVO
├── data/
│   └── viabilidad.db         # ÚNICA FUENTE DE DATOS
├── rag/
│   └── (sin cambios)
├── Documentos/               # sin cambios
├── index.html                # REFACTORIZADO
├── requirements.txt
└── .env.example
```
