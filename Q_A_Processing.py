import torch
import ollama
import os
import argparse
import json
import re

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

# Parse command-line arguments
print(NEON_GREEN + "Parsing command-line arguments..." + RESET_COLOR)
parser = argparse.ArgumentParser(description="Ollama Chat")
parser.add_argument("--model", default="llama3", help="Ollama model to use (default: llama3)")
args = parser.parse_args()

# Load unprocessed emails from file
input_file = "processed_emails.txt"
if os.path.exists(input_file):
    with open(input_file, "r", encoding="utf-8") as q_file:
        input_text = q_file.read()
else:
    print(f"{input_file} does not exist. Exiting.")
    exit(1)

# Analyze and process text
try:
    analysis_result = analyze_and_process_text(input_text, args.model)
    question = analysis_result.get("Question", "").strip()
    answer = analysis_result.get("Answer", "").strip()

    # Save results to formalized_emails.txt
    output_file = "formalized_emails.txt"
    with open(output_file, "w", encoding="utf-8") as a_file:
        a_file.write(f"Question: {question}\n")
        if answer:
            a_file.write(f"Answer: {answer}\n")
        else:
            a_file.write("Answer: [No answer provided]\n")
    
    # Save the question content to question.txt
    question_file = "question.txt"
    with open(question_file, "w", encoding="utf-8") as q_file:
        q_file.write(question)
    
    print(NEON_GREEN + f"All responses saved to {output_file} and question saved to {question_file}" + RESET_COLOR)
except Exception as e:
    print(YELLOW + f"Failed to process input text. Error: {e}" + RESET_COLOR)
