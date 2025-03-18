import os
import tkinter as tk
from tkinter import filedialog, messagebox
import PyPDF2
import re
from tkinterdnd2 import TkinterDnD, DND_FILES
import mysql.connector
from mysql.connector import Error

class PDFProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF/Text Manager with Filter")
        self.root.geometry("400x400")
        
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '1234',
            'database': 'knowledge_db'
        }
        
        self.setup_ui()
        self.init_db()

    def init_db(self):
        """Initialize database connection and ensure tables exist"""
        try:
            conn = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.database = self.db_config['database']
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source_type ENUM('PDF', 'Manual') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
        except Error as e:
            messagebox.showerror("Database Error", f"Initialization failed: {str(e)}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def setup_ui(self):
        """Initialize GUI components"""
        # File operations area
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.pdf_label = tk.Label(file_frame, text="Drag and Drop PDF Here", relief="groove", height=5)
        self.pdf_label.pack(fill=tk.BOTH, expand=True)
        self.pdf_label.drop_target_register(DND_FILES)
        self.pdf_label.dnd_bind('<<Drop>>', self.drop_handler)

        # Text input area
        text_frame = tk.Frame(self.root)
        text_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        self.text_input_label = tk.Label(text_frame, text="Enter Text Below:")
        self.text_input_label.pack(anchor="w")
        
        self.text_input = tk.Text(text_frame, height=5, wrap=tk.WORD)
        self.text_input.pack(fill=tk.BOTH, expand=True)
        
        self.save_button = tk.Button(text_frame, text="Save Text", command=self.save_text)
        self.save_button.pack(pady=5)

        # Filter and delete area
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(pady=10, fill=tk.BOTH)
        
        self.filter_label = tk.Label(filter_frame, text="Delete by Keyword:")
        self.filter_label.pack(anchor="w")
        
        self.filter_entry = tk.Entry(filter_frame)
        self.filter_entry.pack(fill=tk.X, pady=2)
        
        self.delete_button = tk.Button(filter_frame, text="Delete Records", 
                                     command=self.delete_by_keyword, bg="#ff6666")
        self.delete_button.pack(pady=5)

    def drop_handler(self, event):
        """Handle dragged PDF files"""
        file_path = event.data.strip().strip('{}')
        if file_path.lower().endswith('.pdf'):
            self.process_pdf(file_path)
        else:
            messagebox.showerror("Error", "Only PDF files are supported for drag and drop!")

    def process_pdf(self, file_path):
        """Process PDF file and store in database"""
        try:
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ' '.join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
                text = re.sub(r'\s+', ' ', text).strip()
                
                chunks = self.split_text_into_chunks(text)
                
                try:
                    conn = mysql.connector.connect(**self.db_config)
                    cursor = conn.cursor()
                    for chunk in chunks:
                        cursor.execute("""
                            INSERT INTO knowledge_base (content, source_type)
                            VALUES (%s, 'PDF')
                        """, (chunk.strip(),))
                    conn.commit()
                    messagebox.showinfo("Success", "PDF content saved to database!")
                except Error as e:
                    conn.rollback()
                    messagebox.showerror("Database Error", f"Insert failed: {str(e)}")
                finally:
                    if conn.is_connected():
                        cursor.close()
                        conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process PDF: {str(e)}")

    def split_text_into_chunks(self, text, max_chunk_size=1000):
        """Split text into sentence-based chunks"""
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
        """Save manually entered text to database"""
        input_text = self.text_input.get("1.0", "end").strip()
        if input_text:
            try:
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO knowledge_base (content, source_type)
                    VALUES (%s, 'Manual')
                """, (input_text,))
                conn.commit()
                messagebox.showinfo("Success", "Text saved to database!")
            except Error as e:
                conn.rollback()
                messagebox.showerror("Database Error", f"Save failed: {str(e)}")
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        else:
            messagebox.showwarning("Warning", "Input box is empty!")

    def delete_by_keyword(self):
        """Delete records by keyword"""
        keyword = self.filter_entry.get().strip()
        if not keyword:
            messagebox.showwarning("Warning", "Please enter a keyword!")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure to delete all records containing: {keyword}?",
            icon='warning'
        )
        if not confirm:
            return

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM knowledge_base 
                WHERE content LIKE %s
            """, (f"%{keyword}%",))
            deleted_rows = cursor.rowcount
            conn.commit()
            if deleted_rows > 0:
                messagebox.showinfo("Success", f"Deleted {deleted_rows} records containing: {keyword}")
            else:
                messagebox.showinfo("Info", "No matching records found")
        except Error as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"Deletion failed: {str(e)}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = PDFProcessor(root)
    root.mainloop()