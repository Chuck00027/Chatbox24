import os
import tkinter as tk
from tkinter import filedialog, messagebox
import PyPDF2
import re
from tkinterdnd2 import TkinterDnD, DND_FILES

# Function to handle dropped files (PDFs)
def drop_handler(event):
    file_path = event.data.strip().strip('{}')
    if file_path.lower().endswith('.pdf'):
        process_pdf(file_path)
    else:
        messagebox.showerror("Error", "Only PDF files are supported for drag and drop!")

# Function to process PDF files
def process_pdf(file_path):
    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(pdf_reader.pages)
            text = ''
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                if page.extract_text():
                    text += page.extract_text() + " "
            
            # Normalize whitespace and clean up text
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Split text into chunks by sentences, respecting a maximum chunk size
            sentences = re.split(r'(?<=[.!?]) +', text)
            chunks = []
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 < 1000:
                    current_chunk += (sentence + " ").strip()
                else:
                    chunks.append(current_chunk)
                    current_chunk = sentence + " "
            if current_chunk:
                chunks.append(current_chunk)
            
            with open("Knowledge Base.txt", "a", encoding="utf-8") as kb_file:
                for chunk in chunks:
                    kb_file.write(chunk.strip() + "\n")
            messagebox.showinfo("Success", "PDF content appended to Knowledge Base.txt")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to process PDF: {str(e)}")

# Function to save input text directly
def save_text():
    input_text = text_input.get("1.0", "end").strip()
    if input_text:
        try:
            with open("Knowledge Base.txt", "a", encoding="utf-8") as kb_file:
                kb_file.write(input_text + "\n")
            messagebox.showinfo("Success", "Text saved to Knowledge Base.txt")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save text: {str(e)}")
    else:
        messagebox.showwarning("Warning", "Input box is empty!")

# Main window setup
root = TkinterDnD.Tk()
root.title("Drag-and-Drop PDF & Text Input")
root.geometry("400x300")

# PDF Drag-and-Drop Area
pdf_label = tk.Label(root, text="Drag and Drop PDF Here", relief="groove", height=5)
pdf_label.pack(pady=10, fill=tk.BOTH, expand=True)
pdf_label.drop_target_register(DND_FILES)
pdf_label.dnd_bind('<<Drop>>', drop_handler)

# Text Input Box
text_input_label = tk.Label(root, text="Enter Text Below:")
text_input_label.pack(pady=5)
text_input = tk.Text(root, height=5, wrap=tk.WORD)
text_input.pack(pady=5, fill=tk.BOTH, expand=True)

# Save Text Button
save_button = tk.Button(root, text="Save Text", command=save_text)
save_button.pack(pady=10)

# Run the main loop
root.mainloop()
