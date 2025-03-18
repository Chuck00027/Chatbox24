import torch
import ollama
import os
import json
import re
import threading
import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from tkinter import messagebox, ttk

class TrainingProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Email Processor and Formalizer")
        self.root.geometry("800x600")

        self.setup_ui()

    def setup_ui(self):
        self.drop_label = tk.Label(self.root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
        self.drop_label.pack(pady=10, padx=10, fill="both", expand=False)

        self.status_label = tk.Label(self.root, text="Idle", anchor="w")
        self.status_label.pack(padx=10, fill="x")

        self.output_text = tk.Text(self.root, height=20, wrap="word")
        self.output_text.pack(fill="both", padx=10, pady=10, expand=True)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

    def on_drop(self, event):
        file_paths = [match[0] if match[0] else match[1] for match in re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())]
        threading.Thread(target=self.process_files_batch, args=(file_paths,)).start()

    def process_files_batch(self, file_paths):
        for file_path in file_paths:
            if os.path.isfile(file_path) and file_path.endswith(".eml"):
                subject, body = self.process_eml_file(file_path)
                self.update_progress(subject)
                try:
                    analysis_result = self.analyze_and_process_text(body, "llama3")
                    question = analysis_result.get("Question", "").strip()
                    answer = analysis_result.get("Answer", "").strip()

                    # Append to Knowledge Base
                    knowledge_base_file = "Knowledge Base.txt"
                    with open(knowledge_base_file, "a", encoding="utf-8") as kb_file:
                        kb_file.write(f"Question: {question}\n")
                        kb_file.write(f"Answer: {answer if answer else '[No answer provided]'}\n\n")

                    # Display in GUI
                    self.display_response(f"Subject: {subject}\nQuestion: {question}\nAnswer: {answer if answer else '[No answer provided]'}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to process {file_path}. Error: {e}")
            else:
                messagebox.showerror("Invalid File", f"Invalid .eml file: {file_path}")
        self.update_progress("All files processed")

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

    def analyze_and_process_text(self, input_text, ollama_model):
        cleaned_text = self.clean_input_text(input_text)

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

        return json.loads(self.extract_json_from_content(response["message"]["content"]))

    def clean_input_text(self, input_text):
        lines = input_text.splitlines()
        seen = set()
        cleaned_lines = []
        for line in lines:
            if line.strip() not in seen:
                cleaned_lines.append(line.strip())
                seen.add(line.strip())
        return " ".join(cleaned_lines)

    def extract_json_from_content(self, content):
        match = re.search(r'{.*}', content, re.DOTALL)
        if match:
            return match.group(0)
        raise ValueError("No valid JSON content found in the response.")

    def update_progress(self, subject):
        self.status_label.config(text=f"Processing: {subject}...")
        self.root.update_idletasks()

    def display_response(self, response):
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", response)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = TrainingProcessorGUI(root)
    root.mainloop()
