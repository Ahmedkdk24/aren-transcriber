# backend/app.py
import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from docx import Document

# Import your pipeline functions (assumes diarize.py etc. are in same folder)
from diarize import diarize_audio
from transcribe_en import transcribe_english
from transcribe_ar import transcribe_arabic
from translate_ar import translate_arabic

TMP_DIR = "/tmp/aren_transcriber"
os.makedirs(TMP_DIR, exist_ok=True)

app = FastAPI(title="aren-transcriber Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_docx(path: str) -> str:
    """Simple extractor for preview in frontend."""
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paragraphs)

@app.post("/process")
async def process_audio(
    file: UploadFile = File(...),
    language: str = Form(...),              # 'english' or 'arabic'
    moderator_first: bool = Form(False),
    speakers: int = Form(1),
):
    # store upload
    uid = str(uuid.uuid4())[:8]
    in_path = os.path.join(TMP_DIR, f"{uid}_{file.filename}")
    with open(in_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # 1) Diarize
        segments = diarize_audio(in_path, moderator_first=moderator_first, speakers=int(speakers))

        # 2) Transcribe and (optionally) translate
        if language.lower().startswith("en"):
            out_docx = transcribe_english(in_path, segments, speakers=int(speakers), template_path=None)
        elif language.lower().startswith("ar"):
            arabic_docx = transcribe_arabic(in_path, segments, speakers=int(speakers), template_path=None)
            out_docx = translate_arabic(arabic_docx)  # returns path to final EN docx
        else:
            raise HTTPException(status_code=400, detail="Unsupported language")

        # Ensure file is available under TMP_DIR with uid prefix
        final_name = f"{uid}_{os.path.basename(out_docx)}"
        final_path = os.path.join(TMP_DIR, final_name)
        shutil.copy(out_docx, final_path)

        # Extract plain text for preview
        extracted_text = extract_text_from_docx(final_path)

        # Return JSON metadata (frontend will request /download/<final_name> to download)
        return JSONResponse({
            "uid": uid,
            "text": extracted_text,
            "docx_name": final_name,
            "download_url": f"/download/{final_name}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(TMP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=filename)

# If you prefer to run locally:
# uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
