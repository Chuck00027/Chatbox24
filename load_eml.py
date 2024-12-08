import os
import re
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog
import lxml

def clean_text(text):
    """
    Clean and format text to merge multiple lines into a single line, and remove duplicate quoted content.
    """
    text = text.replace("\r", "").replace("\n", " ")  # Remove newlines
    text = re.sub(r'>+\s*', '', text)  # Remove email quote symbols (e.g., ">")
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra whitespace

    # Split the text into the main body and quoted parts
    parts = re.split(r'Am \d{4}-\d{2}-\d{2} \d{2}:\d{2}, schrieb.*?:', text, maxsplit=1)
    main_content = parts[0].strip()  # The unique part (main content)
    quoted_content = parts[1].strip() if len(parts) > 1 else ""

    # If quoted content exists, remove parts of main_content that already appear in quoted_content
    if quoted_content:
        unique_parts = []
        for line in main_content.split(". "):
            if line not in quoted_content:
                unique_parts.append(line)
        main_content = ". ".join(unique_parts).strip()

    # Combine main content and quoted content
    cleaned_text = f"{main_content} {quoted_content}".strip() if quoted_content else main_content
    return cleaned_text

def save_to_file(subject, body, output_file="processed_emails.txt"):
    """Save the subject and body of the email to a text file"""
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"Subject: {subject} | Content: {body}\n")
    print(f"Saved to {output_file}: {subject}")

def get_text_from_html(html_content):
    """Extract plain text from HTML content"""
    soup = BeautifulSoup(html_content, 'lxml')
    return soup.get_text()

def process_eml_file(file_path):
    """Parse and process an .eml file"""
    try:
        with open(file_path, 'rb') as eml_file:
            email_bytes = eml_file.read()
            msg = BytesParser(policy=policy.default).parsebytes(email_bytes)
            
            # Extract subject and body
            subject = msg["subject"] or "No Subject"
            text_content = ""
            
            if msg.is_multipart():
                # If the email has multiple parts, extract text from plain text or HTML parts
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        text_content += part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
                    elif part.get_content_type() == 'text/html':
                        html_content = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
                        text_content += get_text_from_html(html_content)
            else:
                # If the email is not multipart, handle plain text or HTML
                if msg.get_content_type() == 'text/plain':
                    text_content = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))
                elif msg.get_content_type() == 'text/html':
                    text_content = get_text_from_html(msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8')))
            
            # Clean and format the body content
            formatted_text = clean_text(text_content)
            
            # Save the processed email to a file
            save_to_file(subject, formatted_text)
            print(f"Processed file: {file_path}")
            print(f"Subject: {subject}")
    except Exception as e:
        print(f"Failed to process file: {file_path}. Error: {e}")

def select_and_process_eml():
    """Open a file dialog to select and process an .eml file"""
    file_path = filedialog.askopenfilename(filetypes=[("EML Files", "*.eml")])
    if file_path:
        process_eml_file(file_path)

# Create a GUI for file selection
def create_gui():
    root = tk.Tk()
    root.title("EML File Processor")
    root.geometry("300x150")

    select_button = tk.Button(root, text="Select .eml File", command=select_and_process_eml)
    select_button.pack(pady=30)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
