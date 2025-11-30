"""FastAPI application for vector database operations using ChromaDB."""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Research Tool Vector DB",
    description="Vector database service using ChromaDB for semantic search",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
API_KEY = os.getenv("VECTORDB_API_KEY", "dev-vectordb-key-12345")
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", "documents")

# Initialize ChromaDB in-memory client
chroma_client = chromadb.Client(Settings(
    anonymized_telemetry=False,
    allow_reset=True,
))

logger.info("ChromaDB client initialized (in-memory mode)")


# Pydantic models
class Document(BaseModel):
    """Document model for ingestion."""
    id: str = Field(..., description="Unique document ID")
    text: str = Field(..., description="Document text content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Document metadata")


class DocumentBatch(BaseModel):
    """Batch of documents for ingestion."""
    documents: List[Document] = Field(..., description="List of documents to ingest")
    collection_name: Optional[str] = Field(DEFAULT_COLLECTION, description="Collection name")


class QueryRequest(BaseModel):
    """Query request model."""
    query_text: str = Field(..., description="Query text for semantic search")
    n_results: Optional[int] = Field(5, description="Number of results to return", ge=1, le=100)
    collection_name: Optional[str] = Field(DEFAULT_COLLECTION, description="Collection name")
    where: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")
    where_document: Optional[Dict[str, Any]] = Field(None, description="Document content filter")


class QueryResponse(BaseModel):
    """Query response model."""
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")


class CollectionInfo(BaseModel):
    """Collection information model."""
    name: str = Field(..., description="Collection name")
    count: int = Field(..., description="Number of documents in collection")


# Authentication dependency
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key from header."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# Helper functions
def get_or_create_collection(collection_name: str):
    """Get or create a collection."""
    try:
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"description": f"Collection for {collection_name}"}
        )
        return collection
    except Exception as e:
        logger.error(f"Error getting/creating collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to access collection: {str(e)}")


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "research-tool-db",
        "version": "1.0.0",
        "mode": "in-memory"
    }


@app.post("/collections/{collection_name}")
async def create_collection(
    collection_name: str,
    _: str = Depends(verify_api_key)
):
    """Create a new collection."""
    try:
        collection = get_or_create_collection(collection_name)
        return {
            "message": f"Collection '{collection_name}' created successfully",
            "name": collection_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections", response_model=List[CollectionInfo])
async def list_collections(_: str = Depends(verify_api_key)):
    """List all collections."""
    try:
        collections = chroma_client.list_collections()
        return [
            {
                "name": col.name,
                "count": col.count()
            }
            for col in collections
        ]
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{collection_name}")
async def delete_collection(
    collection_name: str,
    _: str = Depends(verify_api_key)
):
    """Delete a collection."""
    try:
        chroma_client.delete_collection(name=collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_documents(
    batch: DocumentBatch,
    _: str = Depends(verify_api_key)
):
    """Ingest documents into the vector database."""
    try:
        collection = get_or_create_collection(batch.collection_name)
        
        # Prepare data for ChromaDB
        ids = [doc.id for doc in batch.documents]
        documents = [doc.text for doc in batch.documents]
        metadatas = [doc.metadata for doc in batch.documents]
        
        # Add documents to collection
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Ingested {len(batch.documents)} documents into '{batch.collection_name}'")
        
        return {
            "message": f"Successfully ingested {len(batch.documents)} documents",
            "collection": batch.collection_name,
            "count": len(batch.documents)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_documents(
    query: QueryRequest,
    _: str = Depends(verify_api_key)
):
    """Query documents using semantic search."""
    try:
        collection = get_or_create_collection(query.collection_name)
        
        # Query the collection
        results = collection.query(
            query_texts=[query.query_text],
            n_results=query.n_results,
            where=query.where,
            where_document=query.where_document
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        logger.info(f"Query returned {len(formatted_results)} results from '{query.collection_name}'")
        
        return {
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    collection_name: str = DEFAULT_COLLECTION,
    _: str = Depends(verify_api_key)
):
    """Delete a document from the collection."""
    try:
        collection = get_or_create_collection(collection_name)
        collection.delete(ids=[document_id])
        
        logger.info(f"Deleted document '{document_id}' from '{collection_name}'")
        
        return {"message": f"Document '{document_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{collection_name}/count")
async def get_collection_count(
    collection_name: str,
    _: str = Depends(verify_api_key)
):
    """Get the number of documents in a collection."""
    try:
        collection = get_or_create_collection(collection_name)
        count = collection.count()
        
        return {
            "collection": collection_name,
            "count": count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
async def reset_database(_: str = Depends(verify_api_key)):
    """Reset the entire database (caution: deletes all data)."""
    try:
        chroma_client.reset()
        logger.warning("Database reset - all collections deleted")
        
        return {"message": "Database reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
