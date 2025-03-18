import torch
import ollama
import os
import re
import json
import threading
import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from sklearn.metrics.pairwise import cosine_similarity
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from tkinter import messagebox, ttk
import hashlib

class TestingProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RAG Semantic Accuracy Tester")
        self.root.geometry("800x600")

        self.vault_filepath = "Knowledge Base.txt"
        self.vault_embeddings_tensor = self.load_or_generate_embeddings()
        self.vault_content = self.load_vault_content()

        self.setup_ui()

    def setup_ui(self):
        drop_label = tk.Label(self.root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
        drop_label.pack(pady=10, padx=10, fill="both", expand=False)

        self.output_text = tk.Text(self.root, height=20, wrap="word")
        self.output_text.pack(fill="both", padx=10, pady=10, expand=True)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

    def compute_file_hash(self, filepath):
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def load_vault_content(self):
        with open(self.vault_filepath, 'r', encoding='utf-8') as f:
            return f.readlines()

    def load_or_generate_embeddings(self, embedding_model='mxbai-embed-large'):
        embeddings_cache_file = 'embeddings_cache.json'
        cache_info_file = 'cache_info.json'

        if not os.path.exists(self.vault_filepath):
            raise FileNotFoundError(f"{self.vault_filepath} does not exist.")

        current_hash = self.compute_file_hash(self.vault_filepath)

        if os.path.exists(cache_info_file):
            with open(cache_info_file, 'r') as f:
                cache_info = json.load(f)
            if cache_info.get('file_hash') == current_hash:
                with open(embeddings_cache_file, 'r') as f:
                    return torch.tensor(json.load(f))

        with open(self.vault_filepath, 'r', encoding='utf-8') as vault_file:
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

    def sparse_context_selection(self, input_text, threshold=0.8, max_k=5):
        input_embedding = ollama.embeddings(model="mxbai-embed-large", prompt=input_text)["embedding"]
        cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), self.vault_embeddings_tensor)
        valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
        top_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)[:max_k]
        return [self.vault_content[idx].strip() for idx in top_indices]

    def generate_rag_response(self, user_input):
        relevant_context = self.sparse_context_selection(user_input)
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

    def calculate_semantic_similarity(self, text1, text2, model="mxbai-embed-large"):
        embedding1 = ollama.embeddings(model=model, prompt=text1)["embedding"]
        embedding2 = ollama.embeddings(model=model, prompt=text2)["embedding"]
        tensor1 = torch.tensor(embedding1).unsqueeze(0)
        tensor2 = torch.tensor(embedding2).unsqueeze(0)
        similarity = cosine_similarity(tensor1, tensor2)[0][0]
        return similarity

    def process_eml_file(self, file_path):
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
        return subject, re.sub(r'\s+', ' ', text_content).strip()

    def process_files_batch(self, file_paths):
        for file_path in file_paths:
            if os.path.isfile(file_path) and file_path.endswith(".eml"):
                subject, body = self.process_eml_file(file_path)
                try:
                    question = body.strip()
                    if not question:
                        self.display_response("Not a standard training file")
                        return
                    rag_response = self.generate_rag_response(question)
                    similarity = self.calculate_semantic_similarity(question, rag_response)
                    accuracy = round(similarity * 100, 2)
                    output_result = (
                        f"Accuracy: {accuracy}%\n"
                        f"Standard Answer: {question}\n"
                        f"RAG Response: {rag_response}"
                    )
                    self.display_response(output_result)
                except Exception as e:
                    messagebox.showerror("Error", f"Error processing {file_path}: {e}")

    def display_response(self, response):
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", response)

    def on_drop(self, event):
        file_paths = [match[0] if match[0] else match[1] for match in re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())]
        threading.Thread(target=self.process_files_batch, args=(file_paths,)).start()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = TestingProcessorGUI(root)
    root.mainloop()
