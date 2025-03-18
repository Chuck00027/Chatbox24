from fastapi import FastAPI, UploadFile, File
import torch
import ollama
import os
import re
import json
from sklearn.metrics.pairwise import cosine_similarity
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
import hashlib

app = FastAPI()

VAULT_FILE = "Knowledge Base.txt"
EMBEDDINGS_CACHE = "embeddings_cache.json"
CACHE_INFO_FILE = "cache_info.json"

def compute_file_hash(filepath):
    """Computes the hash of a file to track changes."""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def load_vault_content():
    """Loads content from the knowledge base file."""
    with open(VAULT_FILE, 'r', encoding='utf-8') as f:
        return f.readlines()

def load_or_generate_embeddings(embedding_model='mxbai-embed-large'):
    """Loads or generates embeddings for the knowledge base."""
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

def sparse_context_selection(input_text, threshold=0.8, max_k=5):
    """Selects relevant context based on similarity threshold."""
    input_embedding = ollama.embeddings(model="mxbai-embed-large", prompt=input_text)["embedding"]
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings_tensor)
    valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
    top_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)[:max_k]
    return [vault_content[idx].strip() for idx in top_indices]

def generate_rag_response(user_input):
    """Generates a response using RAG (Retrieval-Augmented Generation)."""
    relevant_context = sparse_context_selection(user_input)
    context_str = "\n".join(relevant_context) if relevant_context else "No relevant context found."

    prompt = f"""
    User Input:
    {user_input}

    Relevant Context:
    {context_str}

    Response:
    """
    response = ollama.chat(model="llama3", messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]

def calculate_semantic_similarity(text1, text2, model="mxbai-embed-large"):
    """Calculates semantic similarity between two texts."""
    embedding1 = ollama.embeddings(model=model, prompt=text1)["embedding"]
    embedding2 = ollama.embeddings(model=model, prompt=text2)["embedding"]
    tensor1 = torch.tensor(embedding1).unsqueeze(0)
    tensor2 = torch.tensor(embedding2).unsqueeze(0)
    similarity = cosine_similarity(tensor1, tensor2)[0][0]
    return similarity

def process_eml_file(file):
    """Processes an .eml file and extracts subject and body."""
    msg = BytesParser(policy=policy.default).parse(file)
    subject = msg["subject"] or "No Subject"
    text_content = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text_content += part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
    else:
        text_content = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))

    return subject, re.sub(r'\s+', ' ', text_content).strip()

@app.post("/upload_eml/")
async def upload_eml(file: UploadFile = File(...)):
    """Handles uploading of an .eml file for processing."""
    try:
        subject, body = process_eml_file(file.file)
        if not body.strip():
            return {"error": "Not a valid email for testing."}

        rag_response = generate_rag_response(body.strip())
        similarity = calculate_semantic_similarity(body.strip(), rag_response)
        accuracy = round(similarity * 100, 2)

        return {
            "subject": subject,
            "accuracy": f"{accuracy}%",
            "standard_answer": body.strip(),
            "rag_response": rag_response
        }
    except Exception as e:
        return {"error": f"Error processing email: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
