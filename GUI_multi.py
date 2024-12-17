import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
import os
import re
import torch
import ollama
import hashlib
import json
from langdetect import detect
from tkinter import messagebox, ttk
from openai import OpenAI

# ANSI escape codes for colors (for console output)
PINK = '\033[95m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
NEON_GREEN = '\033[92m'
RESET_COLOR = '\033[0m'

# Global variables for batch processing
email_data = {}  # Dictionary to store subjects and responses

# Function to compute file hash
def compute_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

# Load or generate embeddings (same as in rag.py)
def load_or_generate_embeddings(vault_filepath, embedding_model='mxbai-embed-large'):
    embeddings_cache_file = 'embeddings_cache.json'
    cache_info_file = 'cache_info.json'
    
    if not os.path.exists(vault_filepath):
        raise FileNotFoundError(f"{vault_filepath} does not exist.")
    
    current_hash = compute_file_hash(vault_filepath)
    
    if os.path.exists(cache_info_file):
        with open(cache_info_file, 'r') as f:
            cache_info = json.load(f)
        if cache_info.get('file_hash') == current_hash:
            print("Knowledge base unchanged. Loading cached embeddings...")
            with open(embeddings_cache_file, 'r') as f:
                return torch.tensor(json.load(f))
    
    print("Knowledge base changed or no cache found. Generating embeddings...")
    with open(vault_filepath, 'r', encoding='utf-8') as vault_file:
        vault_content = vault_file.readlines()
    
    embeddings = []
    for content in vault_content:
        try:
            response = ollama.embeddings(model=embedding_model, prompt=content.strip())
            embeddings.append(response["embedding"])
        except Exception as e:
            print(f"Failed to generate embedding for content: {content.strip()}\nError: {e}")
    
    with open(embeddings_cache_file, 'w') as f:
        json.dump(embeddings, f)
    with open(cache_info_file, 'w') as f:
        json.dump({'file_hash': current_hash}, f)
    
    return torch.tensor(embeddings)

# Sparse Context Selection
def sparse_context_selection(rewritten_input, vault_embeddings, vault_content, min_k=1, max_k=5, threshold=0.8):
    if vault_embeddings.nelement() == 0:
        return []

    input_embedding = ollama.embeddings(model='mxbai-embed-large', prompt=rewritten_input)["embedding"]
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings)
    
    valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
    if len(valid_indices) < min_k:
        top_indices = torch.topk(cos_scores, k=min_k)[1].tolist()
    else:
        sorted_valid_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)
        top_indices = sorted_valid_indices[:max_k]

    selected_contexts = [vault_content[idx].strip() for idx in top_indices]
    print(f"Selected {len(selected_contexts)} contexts using SCS.")
    return selected_contexts

# Generate response using Ollama with prompt
def generate_response(user_input, vault_embeddings, vault_content, prompt_template):
    relevant_context = sparse_context_selection(user_input, vault_embeddings, vault_content)
    if relevant_context:
        context_str = "\n".join(relevant_context)
        print("Context Pulled from Documents:\n" + CYAN + context_str + RESET_COLOR)
    else:
        print(CYAN + "No relevant context found." + RESET_COLOR)
        context_str = ""
    
    # Detect language of the input
    detected_language = detect(user_input)
    if detected_language == 'de':
        prompt_language = "German"
    else:
        prompt_language = "English"
    
    prompt = prompt_template.format(input=user_input, context=context_str, language=prompt_language)
    client = OpenAI(base_url='http://localhost:11434/v1', api_key='llama3')
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    
    response = client.chat.completions.create(model="llama3", messages=messages, max_tokens=2000)
    return response.choices[0].message.content

# Process .eml file
def process_eml_file(file_path):
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

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

    text_content = re.sub(r'\s+', ' ', text_content).strip()
    return subject, text_content

# GUI Application
def on_drop(event):
    file_paths = re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())  # Handles spaces and {} paths
    global email_data

    for path_group in file_paths:
        file_path = path_group[0] if path_group[0] else path_group[1]
        file_path = file_path.strip()

        if os.path.isfile(file_path) and file_path.endswith(".eml"):
            subject, body = process_eml_file(file_path)
            response = generate_response(body, vault_embeddings_tensor, vault_content, prompt_template)
            email_data[subject] = response
        else:
            messagebox.showerror("Invalid File", f"Invalid .eml file: {file_path}")

    # 更新下拉菜单
    subject_menu['values'] = list(email_data.keys())
    if email_data:
        subject_menu.current(0)
        display_response(email_data[list(email_data.keys())[0]])

def display_response(response):
    output_text.delete("1.0", tk.END)
    output_text.insert("1.0", response)

# Copy to clipboard
def copy_to_clipboard():
    root.clipboard_clear()
    root.clipboard_append(output_text.get("1.0", tk.END).strip())
    root.update()
    messagebox.showinfo("Copied", "Response copied to clipboard!")

# GUI Setup
def create_gui():
    global root, output_text, subject_menu

    root = TkinterDnD.Tk()
    root.title("EML Batch Processor with RAG")
    root.geometry("800x600")

    drop_label = tk.Label(root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
    drop_label.pack(pady=10, padx=10, fill="both", expand=False)

    subject_menu_label = tk.Label(root, text="Select Email Subject:")
    subject_menu_label.pack()

    subject_menu = ttk.Combobox(root, state="readonly")
    subject_menu.pack(fill="x", padx=10)
    subject_menu.bind("<<ComboboxSelected>>", lambda e: display_response(email_data[subject_menu.get()]))

    output_text = tk.Text(root, height=20, wrap="word")
    output_text.pack(fill="both", padx=10, pady=10, expand=True)

    copy_button = tk.Button(root, text="Copy Response", command=copy_to_clipboard)
    copy_button.pack(pady=10)

    root.drop_target_register(DND_FILES)
    root.dnd_bind("<<Drop>>", on_drop)
    root.mainloop()

# Main Program
vault_filepath = "Knowledge Base.txt"
vault_embeddings_tensor = load_or_generate_embeddings(vault_filepath)
with open(vault_filepath, 'r', encoding='utf-8') as f:
    vault_content = f.readlines()

# Prompt template
prompt_template = """
You are a helpful assistant. The user expects a concise and accurate response in {language}. Below is the user's input and relevant context extracted from documents.

User Input:
{input}

Relevant Context:
{context}

Response:
"""

if __name__ == "__main__":
    create_gui()
