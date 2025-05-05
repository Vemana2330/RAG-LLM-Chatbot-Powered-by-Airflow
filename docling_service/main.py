from fastapi import FastAPI, UploadFile, File, HTTPException
from docling_extract import convert_pdf_to_markdown

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/convert_docling/{year}/{quarter}")
async def convert_docling(year: str, quarter: str, file: UploadFile = File(...)):
    try:
        contents = await file.read()
        result = convert_pdf_to_markdown(contents, year, quarter)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))