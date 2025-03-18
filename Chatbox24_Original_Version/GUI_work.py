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

class EmailProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EML Batch Processor with RAG")
        self.root.geometry("800x600")

        self.email_data = {}  # 存储邮件主题和 RAG 生成的回复
        self.vault_filepath = "Knowledge Base.txt"
        self.vault_embeddings_tensor = self.load_or_generate_embeddings()
        self.vault_content = self.load_vault_content()

        self.setup_ui()

    def setup_ui(self):
        drop_label = tk.Label(self.root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
        drop_label.pack(pady=10, padx=10, fill="both", expand=False)

        subject_menu_label = tk.Label(self.root, text="Select Email Subject:")
        subject_menu_label.pack()

        self.subject_menu = ttk.Combobox(self.root, state="readonly")
        self.subject_menu.pack(fill="x", padx=10)
        self.subject_menu.bind("<<ComboboxSelected>>", self.display_response)

        self.output_text = tk.Text(self.root, height=20, wrap="word")
        self.output_text.pack(fill="both", padx=10, pady=10, expand=True)

        copy_button = tk.Button(self.root, text="Copy Response", command=self.copy_to_clipboard)
        copy_button.pack(pady=10)

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

    def sparse_context_selection(self, rewritten_input, min_k=1, max_k=5, threshold=0.8):
        if self.vault_embeddings_tensor.nelement() == 0:
            return []

        input_embedding = ollama.embeddings(model='mxbai-embed-large', prompt=rewritten_input)["embedding"]
        cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), self.vault_embeddings_tensor)

        valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
        if len(valid_indices) < min_k:
            top_indices = torch.topk(cos_scores, k=min_k)[1].tolist()
        else:
            sorted_valid_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)
            top_indices = sorted_valid_indices[:max_k]

        return [self.vault_content[idx].strip() for idx in top_indices]

    def generate_response(self, user_input):
        relevant_context = self.sparse_context_selection(user_input)
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

    def process_eml_file(self, file_path):
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

        return subject, re.sub(r'\s+', ' ', text_content).strip()

    def on_drop(self, event):
        file_paths = re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())

        for path_group in file_paths:
            file_path = path_group[0] if path_group[0] else path_group[1]

            if os.path.isfile(file_path) and file_path.endswith(".eml"):
                subject, body = self.process_eml_file(file_path)
                response = self.generate_response(body)
                self.email_data[subject] = response

        self.subject_menu['values'] = list(self.email_data.keys())
        if self.email_data:
            self.subject_menu.current(0)
            self.display_response()

    def display_response(self, event=None):
        selected_subject = self.subject_menu.get()
        response = self.email_data.get(selected_subject, "No response available.")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", response)

    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output_text.get("1.0", tk.END).strip())
        self.root.update()
        messagebox.showinfo("Copied", "Response copied to clipboard!")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = EmailProcessorGUI(root)
    root.mainloop()
