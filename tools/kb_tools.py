"""
Knowledge base tools using ChromaDB for emigre.eu content.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings


# Initialize ChromaDB client (singleton)
_chroma_client = None


def get_chroma_client():
    """Get or create ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client(ChromaSettings(
            persist_directory=settings.chroma_db_path,
            anonymized_telemetry=False
        ))
    return _chroma_client


def get_or_create_collection(collection_name: str = "emigre_knowledge"):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=collection_name)


def add_knowledge_document(
    doc_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add a document to the knowledge base.

    Args:
        doc_id: Unique document identifier
        content: Document content
        metadata: Optional metadata (url, title, category, etc.)

    Returns:
        Success status
    """
    try:
        collection = get_or_create_collection()
        collection.add(
            documents=[content],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )

        return {"success": True, "doc_id": doc_id}

    except Exception as e:
        return {"success": False, "error": str(e)}


def search_knowledge_base(
    query: str,
    n_results: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Search the knowledge base with semantic similarity.

    Args:
        query: Search query
        n_results: Number of results to return
        filter_metadata: Optional metadata filters

    Returns:
        List of relevant documents with content and metadata
    """
    try:
        collection = get_or_create_collection()

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )

        documents = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                documents.append({
                    "content": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None,
                })

        return documents

    except Exception as e:
        print(f"Error searching knowledge base: {e}")
        return []


def update_knowledge_document(
    doc_id: str,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update an existing knowledge document.

    Args:
        doc_id: Document ID to update
        content: New content (if updating)
        metadata: New metadata (if updating)

    Returns:
        Success status
    """
    try:
        collection = get_or_create_collection()

        update_kwargs = {"ids": [doc_id]}
        if content:
            update_kwargs["documents"] = [content]
        if metadata:
            update_kwargs["metadatas"] = [metadata]

        collection.update(**update_kwargs)

        return {"success": True, "doc_id": doc_id}

    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_knowledge_document(doc_id: str) -> Dict[str, Any]:
    """Delete a document from the knowledge base."""
    try:
        collection = get_or_create_collection()
        collection.delete(ids=[doc_id])
        return {"success": True, "doc_id": doc_id}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_knowledge_documents() -> List[Dict[str, Any]]:
    """Get all documents in the knowledge base."""
    try:
        collection = get_or_create_collection()
        all_docs = collection.get()

        documents = []
        if all_docs['documents']:
            for i, doc in enumerate(all_docs['documents']):
                documents.append({
                    "id": all_docs['ids'][i],
                    "content": doc,
                    "metadata": all_docs['metadatas'][i] if all_docs['metadatas'] else {},
                })

        return documents

    except Exception as e:
        print(f"Error getting all documents: {e}")
        return []


def clear_knowledge_base() -> Dict[str, Any]:
    """Clear all documents from the knowledge base (use with caution)."""
    try:
        client = get_chroma_client()
        client.delete_collection("emigre_knowledge")
        return {"success": True, "message": "Knowledge base cleared"}

    except Exception as e:
        return {"success": False, "error": str(e)}
