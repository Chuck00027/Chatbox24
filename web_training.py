from fastapi import FastAPI, UploadFile, File
import torch
import ollama
import os
import json
import re
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup

app = FastAPI()

VAULT_FILE = "Knowledge Base.txt"

def process_eml_file(file):
    """Processes an .eml file and extracts the email subject and body."""
    msg = BytesParser(policy=policy.default).parse(file)

    subject = msg["subject"] or "No Subject"
    text_content = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text_content += part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
            elif part.get_content_type() == 'text/html':
                html_content = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
                text_content += BeautifulSoup(html_content, 'lxml').get_text()
    else:
        if msg.get_content_type() == 'text/plain':
            text_content = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))
        elif msg.get_content_type() == 'text/html':
            html_content = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))
            text_content = BeautifulSoup(html_content, 'lxml').get_text()

    return subject, re.sub(r'\s+', ' ', text_content).strip()

def analyze_and_process_text(input_text, ollama_model="llama3"):
    """Uses Ollama to analyze the text and extract question-answer pairs."""
    cleaned_text = clean_input_text(input_text)

    prompt = f"""
    Analyze the following text:
    1. Identify semantically meaningful sections of the text, ensuring that content related to the same context is grouped together.
    2. If the text contains both a question and an answer, classify each as 'Question' or 'Answer'.
    3. If the text contains only a single section, classify it as 'Question' without an 'Answer'.
    4. Return only the first question and its corresponding answer if applicable.

    Text:
    {cleaned_text}

    Return the result as a JSON object with the following structure:
    {{
      "Question": "text of the question",
      "Answer": "text of the answer (if applicable, otherwise empty)"
    }}
    """
    response = ollama.chat(model=ollama_model, messages=[{"role": "system", "content": prompt}])

    if "message" not in response or "content" not in response["message"]:
        raise RuntimeError(f"Unexpected response format: {response}")

    return json.loads(extract_json_from_content(response["message"]["content"]))

def clean_input_text(input_text):
    """Removes duplicates and cleans email text."""
    lines = input_text.splitlines()
    seen = set()
    cleaned_lines = []
    for line in lines:
        if line.strip() not in seen:
            cleaned_lines.append(line.strip())
            seen.add(line.strip())
    return " ".join(cleaned_lines)

def extract_json_from_content(content):
    """Extracts JSON structure from Ollama's response."""
    match = re.search(r'{.*}', content, re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("No valid JSON content found in the response.")

@app.post("/upload_eml/")
async def upload_eml(file: UploadFile = File(...)):
    """Handles uploading of an .eml file for analysis and question-answer extraction."""
    try:
        subject, body = process_eml_file(file.file)
        if not body.strip():
            return {"error": "Not a valid email for training."}

        analysis_result = analyze_and_process_text(body.strip())
        question = analysis_result.get("Question", "").strip()
        answer = analysis_result.get("Answer", "").strip()

        # Save to the knowledge base
        with open(VAULT_FILE, "a", encoding="utf-8") as kb_file:
            kb_file.write(f"Question: {question}\n")
            kb_file.write(f"Answer: {answer if answer else '[No answer provided]'}\n\n")

        return {
            "subject": subject,
            "question": question,
            "answer": answer if answer else "[No answer provided]",
            "message": "Data appended to Knowledge Base.txt"
        }
    except Exception as e:
        return {"error": f"Error processing email: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
