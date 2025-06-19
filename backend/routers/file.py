from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4
from datetime import datetime
from ..types import FileRecord
import os

router = APIRouter()

UPLOAD_DIR = "uploads"

@router.post("/upload/{session_id}")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    file_id = str(uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    # Save the file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    file_record = FileRecord(
        id=file_id,
        session_id=session_id,
        filename=file.filename,
        filepath=file_path,
        uploaded_at=datetime.now()
    )
    
    return file_record

@router.get("/{session_id}")
async def list_files(session_id: str):
    # TODO: Implement file listing with proper user validation
    return []

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    # TODO: Implement file deletion with proper user validation
    return {"status": "success"}
