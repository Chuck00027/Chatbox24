from fastapi import FastAPI, UploadFile, File
import torch
import ollama
import os
import re
import json
import hashlib
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from langdetect import detect
from openai import OpenAI

app = FastAPI()

VAULT_FILE = "Knowledge Base.txt"
EMBEDDINGS_CACHE = "embeddings_cache.json"
CACHE_INFO_FILE = "cache_info.json"

email_data = {}  # Stores email subjects and RAG-generated responses

def compute_file_hash(filepath):
    """Computes the hash value of a file."""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def load_vault_content():
    """Loads knowledge base content."""
    with open(VAULT_FILE, 'r', encoding='utf-8') as f:
        return f.readlines()

def load_or_generate_embeddings(embedding_model='mxbai-embed-large'):
    """Loads or generates embedding vectors."""
    if not os.path.exists(VAULT_FILE):
        raise FileNotFoundError(f"{VAULT_FILE} does not exist.")

    current_hash = compute_file_hash(VAULT_FILE)

    if os.path.exists(CACHE_INFO_FILE):
        with open(CACHE_INFO_FILE, 'r') as f:
            cache_info = json.load(f)
        if cache_info.get('file_hash') == current_hash:
            with open(EMBEDDINGS_CACHE, 'r') as f:
                return torch.tensor(json.load(f))

    vault_content = load_vault_content()
    embeddings = []

    for content in vault_content:
        try:
            response = ollama.embeddings(model=embedding_model, prompt=content.strip())
            embeddings.append(response["embedding"])
        except Exception as e:
            print(f"Failed to generate embedding for content: {content.strip()}\nError: {e}")

    with open(EMBEDDINGS_CACHE, 'w') as f:
        json.dump(embeddings, f)
    with open(CACHE_INFO_FILE, 'w') as f:
        json.dump({'file_hash': current_hash}, f)

    return torch.tensor(embeddings)

vault_embeddings_tensor = load_or_generate_embeddings()
vault_content = load_vault_content()

def sparse_context_selection(input_text, min_k=1, max_k=5, threshold=0.8):
    """Selects the most relevant context based on the input."""
    if vault_embeddings_tensor.nelement() == 0:
        return []

    input_embedding = ollama.embeddings(model='mxbai-embed-large', prompt=input_text)["embedding"]
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings_tensor)

    valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
    if len(valid_indices) < min_k:
        top_indices = torch.topk(cos_scores, k=min_k)[1].tolist()
    else:
        sorted_valid_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)
        top_indices = sorted_valid_indices[:max_k]

    return [vault_content[idx].strip() for idx in top_indices]

def generate_response(user_input):
    """Generates a response using Ollama combined with RAG."""
    relevant_context = sparse_context_selection(user_input)
    context_str = "\n".join(relevant_context) if relevant_context else "No relevant context found."

    detected_language = detect(user_input)
    prompt_language = "German" if detected_language == 'de' else "English"

    prompt = f"""
    You are a helpful assistant. The user expects a concise and accurate response in {prompt_language}.
    
    User Input:
    {user_input}

    Relevant Context:
    {context_str}

    Response:
    """

    client = OpenAI(base_url='http://localhost:11434/v1', api_key='llama3')
    messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}]

    response = client.chat.completions.create(model="llama3", messages=messages, max_tokens=2000)
    return response.choices[0].message.content

def process_eml_file(file):
    """Parses .eml files and extracts email subjects and bodies."""
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

@app.post("/upload_eml/")
async def upload_eml(file: UploadFile = File(...)):
    """Handles uploading of an .eml file for parsing and RAG response generation."""
    try:
        subject, body = process_eml_file(file.file)
        if not body.strip():
            return {"error": "Not a valid email for processing."}

        response = generate_response(body.strip())
        email_data[subject] = response

        return {
            "subject": subject,
            "response": response
        }
    except Exception as e:
        return {"error": f"Error processing email: {str(e)}"}

@app.get("/get_subjects/")
def get_subjects():
    """Retrieves all email subjects."""
    return {"subjects": list(email_data.keys())}

@app.get("/get_response/")
def get_response(subject: str):
    """Retrieves the RAG-generated response for a given email subject."""
    return {"subject": subject, "response": email_data.get(subject, "No response available.")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
