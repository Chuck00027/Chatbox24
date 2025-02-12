from fastapi import FastAPI, UploadFile, File, Form
import PyPDF2
import re
import os

app = FastAPI()

def process_pdf(file):
    """Processes a PDF file and extracts text into Knowledge Base.txt"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
        text = ''
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            if page.extract_text():
                text += page.extract_text() + " "

        # Normalize text
        text = re.sub(r'\s+', ' ', text).strip()

        # Split text into chunks
        chunks = split_text_into_chunks(text)

        with open("Knowledge Base.txt", "a", encoding="utf-8") as kb_file:
            for chunk in chunks:
                kb_file.write(chunk.strip() + "\n")

        return {"message": "PDF content appended to Knowledge Base.txt"}

    except Exception as e:
        return {"error": f"Failed to process PDF: {str(e)}"}

def split_text_into_chunks(text, max_chunk_size=1000):
    """Splits text into chunks ensuring each chunk does not exceed max_chunk_size"""
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 < max_chunk_size:
            current_chunk += (sentence + " ").strip()
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """Handles uploading of a PDF file"""
    return process_pdf(file.file)

@app.post("/add_text/")
async def add_text(text: str = Form(...)):
    """Manually input text and save it to Knowledge Base.txt"""
    if text.strip():
        try:
            with open("Knowledge Base.txt", "a", encoding="utf-8") as kb_file:
                kb_file.write(text.strip() + "\n")
            return {"message": "Text saved to Knowledge Base.txt"}
        except Exception as e:
            return {"error": f"Failed to save text: {str(e)}"}
    else:
        return {"error": "Input box is empty!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
