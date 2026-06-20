from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.v1.dependencies import require_tenant_permission
from app.rbac import Permission
from app.schemas import (
    KnowledgeIngestionJob,
    KnowledgeSource,
    KnowledgeSourceCreateRequest,
    QdrantCollectionContract,
)
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
READ_KNOWLEDGE = require_tenant_permission(Permission.READ_KNOWLEDGE)
MANAGE_KNOWLEDGE = require_tenant_permission(Permission.MANAGE_KNOWLEDGE)


@router.get("/sources", response_model=list[KnowledgeSource])
async def list_sources(
    tenant_id: str = Depends(READ_KNOWLEDGE),
    app_store: AppStore = Depends(get_app_store),
) -> list[KnowledgeSource]:
    return app_store.list_knowledge_sources(UUID(tenant_id))


@router.post("/sources", response_model=KnowledgeSource, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: KnowledgeSourceCreateRequest,
    tenant_id: str = Depends(MANAGE_KNOWLEDGE),
    app_store: AppStore = Depends(get_app_store),
) -> KnowledgeSource:
    return app_store.create_knowledge_source(UUID(tenant_id), payload)


@router.post("/upload", response_model=KnowledgeSource, status_code=status.HTTP_201_CREATED)
async def upload_source(
    file: UploadFile = File(...),
    tenant_id: str = Depends(MANAGE_KNOWLEDGE),
    app_store: AppStore = Depends(get_app_store),
) -> KnowledgeSource:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    from app.parsers import extract_text

    content_bytes = await file.read()
    content = extract_text(file.filename, content_bytes)

    if len(content.strip()) < 2:
        raise HTTPException(status_code=400, detail="File content is empty")

    payload = KnowledgeSourceCreateRequest(title=file.filename, source_type="file", content=content)
    return app_store.create_knowledge_source(UUID(tenant_id), payload)


@router.get("/qdrant/contract", response_model=QdrantCollectionContract)
async def qdrant_contract(
    app_store: AppStore = Depends(get_app_store),
) -> QdrantCollectionContract:
    return app_store.qdrant_collection_contract()


@router.get("/ingestion/jobs", response_model=list[KnowledgeIngestionJob])
async def list_ingestion_jobs(
    tenant_id: str = Depends(READ_KNOWLEDGE),
    app_store: AppStore = Depends(get_app_store),
) -> list[KnowledgeIngestionJob]:
    return app_store.list_ingestion_jobs(UUID(tenant_id))


@router.get("/ingestion/jobs/{job_id}", response_model=KnowledgeIngestionJob)
async def get_ingestion_job(
    job_id: UUID,
    tenant_id: str = Depends(READ_KNOWLEDGE),
    app_store: AppStore = Depends(get_app_store),
) -> KnowledgeIngestionJob:
    job = app_store.get_ingestion_job(UUID(tenant_id), job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")
    return job


@router.post(
    "/sources/{source_id}/ingest",
    response_model=KnowledgeIngestionJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_source(
    source_id: UUID,
    tenant_id: str = Depends(MANAGE_KNOWLEDGE),
    app_store: AppStore = Depends(get_app_store),
) -> KnowledgeIngestionJob:
    job = app_store.enqueue_knowledge_ingestion(UUID(tenant_id), source_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )
    return job
