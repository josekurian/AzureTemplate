from fastapi import APIRouter, File, Form, UploadFile

from app.schemas_nlp import (
    TranslationDocumentResponse,
    TranslationTextRequest,
    TranslationTextResponse,
)
from app.services.telemetry_helper import safe_telemetry
from app.services.translator_client import TranslatorClient

router = APIRouter(prefix="/translate", tags=["translation"])
translator_client = TranslatorClient()


@router.post("/text", response_model=TranslationTextResponse)
async def translate_text(request: TranslationTextRequest):
    result = await translator_client.translate_many(
        request.text,
        to_languages=request.to_languages,
        use_glossary=request.use_glossary,
    )
    return TranslationTextResponse(
        detected_language=result["detected_language"],
        translations=result["translations"],
        glossary_applied=result["glossary_applied"],
        telemetry=safe_telemetry(
            feature="translate_text",
            detected_language=result["detected_language"],
            target_language=",".join(request.to_languages),
        ),
    )


@router.post("/document", response_model=TranslationDocumentResponse)
async def translate_document(target_language: str = Form(...), file: UploadFile = File(...)):
    content = await file.read()
    result = await translator_client.translate_document(file.filename, content, target_language=target_language)
    return TranslationDocumentResponse(
        status=result["status"],
        filename=result["filename"],
        target_language=result["target_language"],
        translated_filename=result["translated_filename"],
        telemetry=safe_telemetry(
            feature="translate_document",
            target_language=target_language,
        ),
    )
