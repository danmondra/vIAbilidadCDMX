"""
RAG Document Indexer for ViableCDMX
====================================
Indexes official PDF documents (LEM, reglamentos, guías SIAPEM) into a
ChromaDB vector store using LlamaIndex + Claude as the LLM backbone.

Run once before starting the bot:
    python rag/indexer.py

Then query the index from the bot via rag/query.py (or inline in the service).
"""

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Documents to place in rag/documents/ for full RAG support
EXPECTED_DOCUMENTS = [
    {
        "filename": "ley_establecimientos.pdf",
        "descripcion": "Ley de Establecimientos Mercantiles de la CDMX (LEM 2025)",
        "url": "https://prontuario.cdmx.gob.mx/pdf/Ley%20Establecimientos%20Mercantiles%2024122025.pdf",
    },
    {
        "filename": "reglamento_lem.pdf",
        "descripcion": "Reglamento de la Ley de Establecimientos Mercantiles",
        "url": "https://www.cdmx.gob.mx/gobierno/documentos/reglamento-lem",
    },
    {
        "filename": "guia_siapem.pdf",
        "descripcion": "Guía de usuario SIAPEM — cómo dar de alta un negocio",
        "url": "https://siapem.cdmx.gob.mx/guia_usuario.pdf",
    },
    {
        "filename": "uso_suelo_seduvi.pdf",
        "descripcion": "Programa General de Ordenamiento Territorial CDMX (uso de suelo)",
        "url": "https://www.seduvi.cdmx.gob.mx/programas/pgot",
    },
]


def _print_missing_docs_help(docs_dir: Path) -> None:
    print("\n" + "=" * 60)
    print("Directorio rag/documents/ vacio o sin PDFs.")
    print("Coloca los siguientes PDFs en:", docs_dir)
    print("=" * 60)
    for doc in EXPECTED_DOCUMENTS:
        print(f"\n  Archivo  : {doc['filename']}")
        print(f"  Que es   : {doc['descripcion']}")
        print(f"  Descarga : {doc['url']}")
    print("\nLuego vuelve a ejecutar: python rag/indexer.py")
    print("=" * 60 + "\n")


def index_documents() -> bool:
    """
    Index all PDFs in rag/documents/ into a ChromaDB vector store.

    Returns True on success, False if there was an error.
    The index is persisted to rag/chroma_db/ for reuse.
    """
    docs_dir = Path(__file__).parent / "documents"
    chroma_dir = Path(__file__).parent / "chroma_db"

    # Ensure docs directory exists
    if not docs_dir.exists():
        print(f"Creando directorio {docs_dir} ...")
        docs_dir.mkdir(parents=True, exist_ok=True)

    # Check for PDFs and MDs
    pdf_files = list(docs_dir.glob("*.pdf"))
    md_files = list(docs_dir.glob("*.md"))
    all_files = pdf_files + md_files

    if not all_files:
        _print_missing_docs_help(docs_dir)
        return False

    print(f"Encontrados {len(all_files)} archivo(s) para indexar:")
    for f in all_files:
        print(f"  - {f.name} ({f.stat().st_size // 1024} KB)")

    # Validate API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nERROR: ANTHROPIC_API_KEY no encontrada en .env")
        print("Agrega tu API key al archivo .env antes de indexar.")
        return False

    try:
        from llama_index.core import (
            VectorStoreIndex,
            SimpleDirectoryReader,
            StorageContext,
            Settings,
        )
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.llms.anthropic import Anthropic
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore

    except ImportError as e:
        print(f"\nERROR de importacion: {e}")
        print("\nInstala las dependencias con:")
        print(
            "  pip install llama-index chromadb llama-index-llms-anthropic "
            "llama-index-embeddings-huggingface llama-index-vector-stores-chroma "
            "sentence-transformers"
        )
        return False

    print("\nCargando documentos...")
    try:
        reader = SimpleDirectoryReader(
            input_dir=str(docs_dir),
            required_exts=[".pdf", ".md"],
            recursive=False,
        )
        documents = reader.load_data()
    except Exception as e:
        print(f"ERROR al cargar documentos: {e}")
        return False

    if not documents:
        print("No se pudieron cargar documentos. Verifica que los PDFs no esten corruptos.")
        return False

    print(f"Cargados {len(documents)} fragmentos de {len(pdf_files)} archivo(s).")

    # Configure LlamaIndex settings
    print("\nConfigurando modelos...")
    try:
        # Use a lightweight local embedding model to avoid API costs
        embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5",
        )

        llm = Anthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            max_tokens=4096,
        )

        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=64,
        )
    except Exception as e:
        print(f"ERROR configurando modelos: {e}")
        return False

    # Set up ChromaDB persistent store
    print(f"\nInicializando ChromaDB en {chroma_dir} ...")
    chroma_dir.mkdir(parents=True, exist_ok=True)

    try:
        chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
        chroma_collection = chroma_client.get_or_create_collection(
            name="viable_cdmx_docs",
            metadata={"hnsw:space": "cosine"},
        )
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
    except Exception as e:
        print(f"ERROR inicializando ChromaDB: {e}")
        return False

    # Build the index
    print("Indexando documentos (esto puede tomar varios minutos)...")
    try:
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True,
        )
    except Exception as e:
        print(f"ERROR durante el indexado: {e}")
        return False

    # Persist storage context (nodes, docstore, etc.)
    index.storage_context.persist(persist_dir=str(chroma_dir))

    print("\n" + "=" * 60)
    print("INDEXADO EXITOSO")
    print(f"  Fragmentos indexados : {len(documents)}")
    print(f"  Archivos procesados  : {len(pdf_files)}")
    print(f"  Indice guardado en   : {chroma_dir}")
    print("=" * 60)
    print("\nAhora puedes iniciar el bot: python bot/main.py")
    return True


def load_index():
    """
    Load the existing ChromaDB index for querying.
    Call this from the bot's RAG service instead of re-indexing every time.

    Returns a LlamaIndex QueryEngine or None if the index doesn't exist.
    """
    chroma_dir = Path(__file__).parent / "chroma_db"

    if not chroma_dir.exists():
        print("Indice no encontrado. Ejecuta primero: python rag/indexer.py")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY no encontrada en .env")
        return None

    try:
        from llama_index.core import VectorStoreIndex, StorageContext, Settings
        from llama_index.llms.anthropic import Anthropic
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore

        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        llm = Anthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            max_tokens=2048,
        )
        Settings.llm = llm
        Settings.embed_model = embed_model

        chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
        # Try both collection names for backwards compatibility
        existing = [c.name for c in chroma_client.list_collections()]
        col_name = "viablecdmx" if "viablecdmx" in existing else "viable_cdmx_docs"
        chroma_collection = chroma_client.get_or_create_collection(col_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
        )
        return index.as_query_engine(similarity_top_k=5)

    except ImportError:
        print("Dependencias RAG no instaladas. Usando solo datos estructurados.")
        return None
    except Exception as e:
        print(f"ERROR cargando indice RAG: {e}")
        return None


if __name__ == "__main__":
    success = index_documents()
    sys.exit(0 if success else 1)
