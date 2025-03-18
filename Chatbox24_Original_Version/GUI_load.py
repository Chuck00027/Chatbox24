import os
import tkinter as tk
from tkinter import filedialog, messagebox
import PyPDF2
import re
from tkinterdnd2 import TkinterDnD, DND_FILES

class PDFProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Drag-and-Drop PDF & Text Input")
        self.root.geometry("400x300")

        self.setup_ui()

    def setup_ui(self):
        """初始化 GUI 组件"""
        self.pdf_label = tk.Label(self.root, text="Drag and Drop PDF Here", relief="groove", height=5)
        self.pdf_label.pack(pady=10, fill=tk.BOTH, expand=True)
        self.pdf_label.drop_target_register(DND_FILES)
        self.pdf_label.dnd_bind('<<Drop>>', self.drop_handler)

        self.text_input_label = tk.Label(self.root, text="Enter Text Below:")
        self.text_input_label.pack(pady=5)

        self.text_input = tk.Text(self.root, height=5, wrap=tk.WORD)
        self.text_input.pack(pady=5, fill=tk.BOTH, expand=True)

        self.save_button = tk.Button(self.root, text="Save Text", command=self.save_text)
        self.save_button.pack(pady=10)

    def drop_handler(self, event):
        """处理拖拽的 PDF 文件"""
        file_path = event.data.strip().strip('{}')
        if file_path.lower().endswith('.pdf'):
            self.process_pdf(file_path)
        else:
            messagebox.showerror("Error", "Only PDF files are supported for drag and drop!")

    def process_pdf(self, file_path):
        """解析 PDF 文件并提取文本存入 Knowledge Base.txt"""
        try:
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                text = ''
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    if page.extract_text():
                        text += page.extract_text() + " "

                # 规范化文本
                text = re.sub(r'\s+', ' ', text).strip()

                # 处理文本分块
                chunks = self.split_text_into_chunks(text)

                with open("Knowledge Base.txt", "a", encoding="utf-8") as kb_file:
                    for chunk in chunks:
                        kb_file.write(chunk.strip() + "\n")

                messagebox.showinfo("Success", "PDF content appended to Knowledge Base.txt")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process PDF: {str(e)}")

    def split_text_into_chunks(self, text, max_chunk_size=1000):
        """按句子拆分文本，确保每个 chunk 不超过 max_chunk_size"""
        sentences = re.split(r'(?<=[.!?]) +', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 < max_chunk_size:
                current_chunk += (sentence + " ").strip()
            else:
                chunks.append(current_chunk)
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def save_text(self):
        """手动输入文本并保存到 Knowledge Base.txt"""
        input_text = self.text_input.get("1.0", "end").strip()
        if input_text:
            try:
                with open("Knowledge Base.txt", "a", encoding="utf-8") as kb_file:
                    kb_file.write(input_text + "\n")
                messagebox.showinfo("Success", "Text saved to Knowledge Base.txt")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save text: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Input box is empty!")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = PDFProcessorGUI(root)
    root.mainloop()
