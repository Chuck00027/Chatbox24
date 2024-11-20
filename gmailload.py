import imaplib
import email
from email import policy
from email.parser import BytesParser
from datetime import datetime
import os
import re
import argparse
from bs4 import BeautifulSoup
import lxml
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def chunk_text(text, max_length=1000):
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\s*(?:>\s*){2,}', ' ', text)
    text = re.sub(r'-{3,}', ' ', text)
    text = re.sub(r'_{3,}', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 < max_length:
            current_chunk += (sentence + " ").strip()
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def save_to_vault_and_sample(chunks, subject, body):
    # Save to Knowledge Base.txt
    with open("Knowledge Base.txt", "a", encoding="utf-8") as vault_file:
        for chunk in chunks:
            vault_file.write(chunk.strip() + "\n")
    
    # Save to Standard Q&A.txt
    with open("Standard Q&A.txt", "a", encoding="utf-8") as sample_file:
        sample_file.write(f"Question: {subject}\n")
        sample_file.write(f"Answer: {body}\n\n")

def get_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    return soup.get_text()

def process_email(email_bytes):
    msg = BytesParser(policy=policy.default).parsebytes(email_bytes)
    subject = msg["subject"] or "No Subject"
    text_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text_content += part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
            elif part.get_content_type() == 'text/html':
                html_content = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
                text_content += get_text_from_html(html_content)
    else:
        if msg.get_content_type() == 'text/plain':
            text_content = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))
        elif msg.get_content_type() == 'text/html':
            text_content = get_text_from_html(msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8')))
    
    chunks = chunk_text(text_content)
    save_to_vault_and_sample(chunks, subject, text_content)
    return subject, text_content

def search_and_process_emails(imap_client, search_keyword, start_date, end_date, label=None):
    search_criteria = 'ALL'
    if label:
        search_criteria = f'X-GM-LABELS "{label}"'
    elif start_date and end_date:
        search_criteria = f'(SINCE "{start_date}" BEFORE "{end_date}")'
    if search_keyword:
        search_criteria += f' BODY "{search_keyword}"'

    print(f"Using search criteria: {search_criteria}")
    typ, data = imap_client.search(None, search_criteria)
    if typ == 'OK':
        email_ids = data[0].split()
        print(f"Found {len(email_ids)} emails matching criteria.")
        for num in email_ids:
            typ, email_data = imap_client.fetch(num, '(RFC822)')
            if typ == 'OK':
                email_id = num.decode('utf-8')
                print(f"Processing email ID: {email_id}")
                subject, body = process_email(email_data[0][1])
                print(f"Saved: {subject}")
            else:
                print(f"Failed to fetch email ID: {num.decode('utf-8')}")
    else:
        print("No emails found matching criteria.")

def main():
    parser = argparse.ArgumentParser(description="Search and process emails.")
    parser.add_argument("--keyword", help="Keyword to search in email bodies.", default="")
    parser.add_argument("--startdate", help="Start date in DD.MM.YYYY format.", required=False)
    parser.add_argument("--enddate", help="End date in DD.MM.YYYY format.", required=False)
    parser.add_argument("--label", help="Label to search emails with.", required=False)
    args = parser.parse_args()

    start_date = None
    end_date = None

    if args.startdate and args.enddate:
        try:
            start_date = datetime.strptime(args.startdate, "%d.%m.%Y").strftime("%d-%b-%Y")
            end_date = datetime.strptime(args.enddate, "%d.%m.%Y").strftime("%d-%b-%Y")
        except ValueError as e:
            print(f"Error: Invalid date format. Use DD.MM.YYYY. Details: {e}")
            return

    gmail_username = os.getenv('GMAIL_USERNAME')
    gmail_password = os.getenv('GMAIL_PASSWORD')

    M = imaplib.IMAP4_SSL('imap.gmail.com')
    M.login(gmail_username, gmail_password)
    M.select('inbox')

    search_and_process_emails(M, args.keyword, start_date, end_date, args.label)

    M.logout()

if __name__ == "__main__":
    main()
