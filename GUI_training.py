import torch
import ollama
import os
import argparse
import json
import re
import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from tkinter import messagebox, ttk
import threading

# ANSI escape codes for colors
PINK = '\033[95m'
YELLOW = '\033[93m'
NEON_GREEN = '\033[92m'
RESET_COLOR = '\033[0m'

# Function to clean input text
def clean_input_text(input_text):
    """
    Simplify and clean the input text by removing repeated sections and unnecessary formatting.
    """
    lines = input_text.splitlines()
    seen = set()
    cleaned_lines = []
    for line in lines:
        if line.strip() not in seen:
            cleaned_lines.append(line.strip())
            seen.add(line.strip())
    return " ".join(cleaned_lines)

# Function to extract JSON from response content
def extract_json_from_content(content):
    """
    Extract the JSON part from the response content.
    """
    match = re.search(r'{.*}', content, re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("No valid JSON content found in the response.")

# Function to analyze and process text using Ollama
def analyze_and_process_text(input_text, ollama_model):
    """
    Analyze the input text to separate it into semantically meaningful sections and identify questions and answers.
    """
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
    print(YELLOW + "DEBUG: Ollama response:\n" + str(response) + RESET_COLOR)
    
    # Extract and parse the JSON from response content
    if "message" not in response or "content" not in response["message"]:
        raise RuntimeError(f"Unexpected response format: {response}")
    raw_content = response["message"]["content"]
    json_content = extract_json_from_content(raw_content)
    return json.loads(json_content)

# Function to process .eml file
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

# Function to update progress in the GUI
def update_progress(subject):
    status_label.config(text=f"Processing: {subject}...")
    root.update_idletasks()

def process_files_batch(file_paths):
    for file_path in file_paths:
        if os.path.isfile(file_path) and file_path.endswith(".eml"):
            subject, body = process_eml_file(file_path)
            update_progress(subject)
            try:
                analysis_result = analyze_and_process_text(body, "llama3")
                question = analysis_result.get("Question", "").strip()
                answer = analysis_result.get("Answer", "").strip()
                
                # Append to Knowledge Base
                knowledge_base_file = "Knowledge Base.txt"
                with open(knowledge_base_file, "a", encoding="utf-8") as kb_file:
                    kb_file.write(f"Question: {question}\n")
                    if answer:
                        kb_file.write(f"Answer: {answer}\n")
                    else:
                        kb_file.write("Answer: [No answer provided]\n")
                    kb_file.write("\n")

                # Display in GUI
                display_response(f"Subject: {subject}\nQuestion: {question}\nAnswer: {answer if answer else '[No answer provided]'}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process {file_path}. Error: {e}")
        else:
            messagebox.showerror("Invalid File", f"Invalid .eml file: {file_path}")
    update_progress("All files processed")

def on_drop(event):
    file_paths = [match[0] if match[0] else match[1] for match in re.findall(r'\{(.*?)\}|([^{}]+)', event.data.strip())]
    threading.Thread(target=process_files_batch, args=(file_paths,)).start()

def display_response(response):
    output_text.delete("1.0", tk.END)
    output_text.insert("1.0", response)

def create_gui():
    global root, output_text, status_label
    root = TkinterDnD.Tk()
    root.title("Email Processor and Formalizer")
    root.geometry("800x600")

    drop_label = tk.Label(root, text="Drag and drop your .eml files here", bg="lightgrey", relief="solid")
    drop_label.pack(pady=10, padx=10, fill="both", expand=False)

    status_label = tk.Label(root, text="Idle", anchor="w")
    status_label.pack(padx=10, fill="x")

    output_text = tk.Text(root, height=20, wrap="word")
    output_text.pack(fill="both", padx=10, pady=10, expand=True)

    root.drop_target_register(DND_FILES)
    root.dnd_bind("<<Drop>>", on_drop)
    root.mainloop()

if __name__ == "__main__":
    create_gui()
