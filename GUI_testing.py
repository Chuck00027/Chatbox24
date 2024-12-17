import torch
import ollama
import os
import re
import json
import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from sklearn.metrics.pairwise import cosine_similarity
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from tkinter import messagebox, ttk
import threading
import hashlib

# 全局变量
vault_filepath = "Knowledge Base.txt"
vault_embeddings_tensor = torch.tensor([])
vault_content = []

# 计算文件哈希
def compute_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

# 生成嵌入或加载缓存
def load_or_generate_embeddings(vault_filepath, embedding_model='mxbai-embed-large'):
    embeddings_cache_file = 'embeddings_cache.json'
    cache_info_file = 'cache_info.json'

    if not os.path.exists(vault_filepath):
        raise FileNotFoundError(f"{vault_filepath} does not exist.")

    current_hash = compute_file_hash(vault_filepath)

    # 使用缓存
    if os.path.exists(cache_info_file):
        with open(cache_info_file, 'r') as f:
            cache_info = json.load(f)
        if cache_info.get('file_hash') == current_hash:
            with open(embeddings_cache_file, 'r') as f:
                return torch.tensor(json.load(f))

    # 生成新嵌入
    embeddings = []
    with open(vault_filepath, 'r', encoding='utf-8') as f:
        vault_lines = f.readlines()
    for line in vault_lines:
        if line.strip():  # 避免处理空行
            response = ollama.embeddings(model=embedding_model, prompt=line.strip())
            embeddings.append(response["embedding"])
    with open(embeddings_cache_file, 'w') as f:
        json.dump(embeddings, f)
    with open(cache_info_file, 'w') as f:
        json.dump({'file_hash': current_hash}, f)
    return torch.tensor(embeddings)

# 稀疏上下文选择
def sparse_context_selection(input_text, vault_embeddings, vault_content, threshold=0.8, max_k=5):
    input_embedding = ollama.embeddings(model="mxbai-embed-large", prompt=input_text)["embedding"]
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings)
    valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
    top_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)[:max_k]
    return [vault_content[idx].strip() for idx in top_indices]

# 生成 RAG 回答
def generate_rag_response(user_input, vault_embeddings, vault_content):
    relevant_context = sparse_context_selection(user_input, vault_embeddings, vault_content)
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

# 计算语义相似度
def calculate_semantic_similarity(text1, text2, model="mxbai-embed-large"):
    embedding1 = ollama.embeddings(model=model, prompt=text1)["embedding"]
    embedding2 = ollama.embeddings(model=model, prompt=text2)["embedding"]
    tensor1 = torch.tensor(embedding1).unsqueeze(0)
    tensor2 = torch.tensor(embedding2).unsqueeze(0)
    similarity = cosine_similarity(tensor1, tensor2)[0][0]
    return similarity

# 处理 .eml 文件
def process_eml_file(file_path):
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    subject = msg["subject"] or "No Subject"
    text_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text_content += part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
    else:
        text_content = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))
    text_content = re.sub(r'\s+', ' ', text_content).strip()
    return subject, text_content

# 批量处理文件
def process_files_batch(file_paths):
    for file_path in file_paths:
        if os.path.isfile(file_path) and file_path.endswith(".eml"):
            subject, body = process_eml_file(file_path)
            try:
                question = body.strip()
                if not question:
                    display_response("Not a standard training file")
                    return
                rag_response = generate_rag_response(question, vault_embeddings_tensor, vault_content)
                similarity = calculate_semantic_similarity(question, rag_response)
                accuracy = round(similarity * 100, 2)
                output_result = (
                    f"Accuracy: {accuracy}%\n"
                    f"Standard Answer: {question}\n"
                    f"RAG Response: {rag_response}"
                )
                display_response(output_result)
            except Exception as e:
                messagebox.showerror("Error", f"Error processing {file_path}: {e}")

# GUI 相关功能
def display_response(response):
    output_text.delete("1.0", tk.END)
    output_text.insert("1.0", response)

def on_drop(event):
    file_paths = [match[0] if match[0] else match[1] for match in re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())]
    threading.Thread(target=process_files_batch, args=(file_paths,)).start()

def create_gui():
    global root, output_text
    root = TkinterDnD.Tk()
    root.title("RAG Semantic Accuracy Tester")
    root.geometry("800x600")

    drop_label = tk.Label(root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
    drop_label.pack(pady=10, padx=10, fill="both", expand=False)

    output_text = tk.Text(root, height=20, wrap="word")
    output_text.pack(fill="both", padx=10, pady=10, expand=True)

    root.drop_target_register(DND_FILES)
    root.dnd_bind("<<Drop>>", on_drop)
    root.mainloop()

if __name__ == "__main__":
    vault_embeddings_tensor = load_or_generate_embeddings(vault_filepath)
    with open(vault_filepath, 'r', encoding='utf-8') as f:
        vault_content = f.readlines()
    create_gui()
