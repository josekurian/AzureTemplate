from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import os
from app.services.document_intelligence_adapter import DocumentIntelligenceAdapter
from app.services.azure_openai_adapter import AzureOpenAIAdapter
from app.services.cognitive_search_adapter import CognitiveSearchAdapter
from app.ingestion.orchestrator import IngestionOrchestrator
from app.core.config import settings

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # save to temp
    try:
        suffix = os.path.splitext(file.filename)[1] or '.bin'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    # If extraction is desired
    docint = DocumentIntelligenceAdapter(mock_mode=settings.MOCK_MODE)
    try:
        extraction = await docint.extract_invoice(tmp_path)
    except Exception as e:
        extraction = {"error": str(e)}

    # Optionally run ingestion pipeline to index
    orchestrator = IngestionOrchestrator(embedder=AzureOpenAIAdapter(mock_mode=settings.MOCK_MODE), indexer=CognitiveSearchAdapter(mock_mode=settings.MOCK_MODE))
    try:
        ingest_res = await orchestrator.ingest([{"id": os.path.basename(tmp_path), "text": extraction.get('vendor','') + ' ' + str(extraction)}])
    except Exception as e:
        ingest_res = {"error": str(e)}

    # cleanup
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    return {"filename": file.filename, "extraction": extraction, "ingest": ingest_res}
