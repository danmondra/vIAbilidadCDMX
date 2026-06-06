# Setup RAG — ViableCDMX

## Documentos oficiales a descargar

Colocar en `rag/documents/` antes de correr el indexer:

| Archivo esperado | Descripción | URL de descarga |
|------------------|-------------|-----------------|
| `ley_establecimientos.pdf` | Ley de Establecimientos Mercantiles CDMX 2025 (LEM) | https://prontuario.cdmx.gob.mx/pdf/Ley%20Establecimientos%20Mercantiles%2024122025.pdf |
| `reglamento_lem.pdf` | Reglamento de la Ley de Establecimientos Mercantiles | https://www.cdmx.gob.mx/gobierno/documentos/reglamento-lem |
| `guia_siapem.pdf` | Guía de usuario SIAPEM — alta de negocio | https://siapem.cdmx.gob.mx |
| `uso_suelo_seduvi.pdf` | Programa General de Ordenamiento Territorial CDMX | https://www.seduvi.cdmx.gob.mx/programas/pgot |

## Alternativa rápida (hackathon)

Los archivos en `Documentos/` ya cubren el conocimiento necesario. Copiarlos al RAG:

```bash
copy "Documentos\catalogos_giros.pdf" "rag\documents\"
copy "Documentos\Manuales Cenproin.md" "rag\documents\"
copy "Documentos\Flujo_Maestro_Asesoramiento.md" "rag\documents\"
copy "Documentos\Esquema_Flujo.md" "rag\documents\"
```

## Instalación de dependencias RAG

```bash
pip install llama-index chromadb llama-index-llms-anthropic llama-index-embeddings-huggingface
```

## Correr el indexer

```bash
python rag/indexer.py
```

El índice se guarda en `rag/chroma_db/` (ignorado por git). Solo se necesita correr una vez, o cada vez que se agreguen documentos nuevos.

## Consultar el índice desde el bot

El servicio `bot/services/ai_service.py` ya tiene integración RAG via `responder_pregunta_tramite()`. Una vez indexado, el bot responde preguntas libres sobre trámites citando los documentos oficiales.

## Datos DENUE reales (opcional)

Para competencia real en lugar de la muestra sintética:

1. Descargar CSV de INEGI: https://www.inegi.org.mx/app/descarga/ficha.html?tit=3615697&ag=9&f=csv
2. Renombrar a `denue_cdmx.csv` y colocar en `data/`
3. El servicio `bot/services/denue_service.py` lo detecta automáticamente
