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
import mysql.connector
from mysql.connector import Error

class TrainingProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("Email Processor and Formalizer")
        self.root.geometry("800x600")

        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '1234',  # Update to your actual password
            'database': 'knowledge_db'
        }

        self.setup_ui()

    def setup_ui(self):
        """Initialize GUI components"""
        self.drop_label = tk.Label(self.root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
        self.drop_label.pack(pady=10, padx=10, fill="both", expand=False)

        self.status_label = tk.Label(self.root, text="Idle", anchor="w")
        self.status_label.pack(padx=10, fill="x")

        self.output_text = tk.Text(self.root, height=20, wrap="word")
        self.output_text.pack(fill="both", padx=10, pady=10, expand=True)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

    def on_drop(self, event):
        """Handle file drop event"""
        file_paths = [match[0] if match[0] else match[1] for match in re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())]
        threading.Thread(target=self.process_files_batch, args=(file_paths,)).start()

    def process_files_batch(self, file_paths):
        """Batch process files and store in database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            for file_path in file_paths:
                if os.path.isfile(file_path) and file_path.endswith(".eml"):
                    try:
                        # Process EML file
                        subject, body = self.process_eml_file(file_path)
                        self.update_progress(subject)
                        
                        # Analyze text content
                        analysis_result = self.analyze_and_process_text(body, "llama3")
                        question = analysis_result.get("Question", "").strip()
                        answer = analysis_result.get("Answer", "").strip()
                        
                        # Build database record
                        combined_content = f"Question: {question}\nAnswer: {answer if answer else '[No answer provided]'}"
                        
                        # Insert into database
                        cursor.execute("""
                            INSERT INTO knowledge_base (content, source_type)
                            VALUES (%s, 'Email')
                        """, (combined_content,))
                        
                        # Display processing result
                        self.display_response(f"Subject: {subject}\n{combined_content}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to process file: {file_path}\nError: {str(e)}")
                else:
                    messagebox.showerror("Invalid File", f"Non-.eml file: {file_path}")
            
            # Commit transaction
            conn.commit()
            self.update_progress("All files processed")
            
        except Error as e:
            messagebox.showerror("Database Error", f"Database operation failed: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def process_eml_file(self, file_path):
        """Parse EML file content"""
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
        """Analyze text using LLM"""
        cleaned_text = self.clean_input_text(input_text)

        prompt = f"""
        Analyze the following text:
        1. Identify semantically meaningful parts
        2. If containing Q&A, label as Question and Answer
        3. If only single part, label as Question
        4. Return the first valid Q/A pair

        Text content:
        {cleaned_text}

        Return JSON format:
        {{
          "Question": "Question content",
          "Answer": "Answer content (omit if none)"
        }}
        """
        response = ollama.chat(model=ollama_model, messages=[{"role": "system", "content": prompt}])

        if "message" not in response or "content" not in response["message"]:
            raise RuntimeError(f"Invalid response format: {response}")

        return json.loads(self.extract_json_from_content(response["message"]["content"]))

    def clean_input_text(self, input_text):
        """Clean duplicate content"""
        lines = input_text.splitlines()
        seen = set()
        return " ".join([line.strip() for line in lines if line.strip() and line.strip() not in seen])

    def extract_json_from_content(self, content):
        """Extract JSON from response content"""
        match = re.search(r'{.*}', content, re.DOTALL)
        if match:
            return match.group(0)
        raise ValueError("No valid JSON found in response")

    def update_progress(self, message):
        """Update status bar"""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def display_response(self, response):
        """Display processing result"""
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", response)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = TrainingProcessor(root)
    root.mainloop()