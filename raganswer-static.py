import torch
import ollama
import os
import hashlib
import json
import argparse
from openai import OpenAI

# ANSI escape codes for colors
PINK = '\033[95m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
NEON_GREEN = '\033[92m'
RESET_COLOR = '\033[0m'

# Function to compute file hash
def compute_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

# Function to load or generate embeddings
def load_or_generate_embeddings(vault_filepath, embedding_model='mxbai-embed-large'):
    embeddings_cache_file = 'embeddings_cache.json'
    cache_info_file = 'cache_info.json'
    
    if not os.path.exists(vault_filepath):
        raise FileNotFoundError(f"{vault_filepath} does not exist.")
    
    current_hash = compute_file_hash(vault_filepath)
    
    if os.path.exists(cache_info_file):
        with open(cache_info_file, 'r') as f:
            cache_info = json.load(f)
        if cache_info.get('file_hash') == current_hash:
            print("Knowledge base unchanged. Loading cached embeddings...")
            with open(embeddings_cache_file, 'r') as f:
                return torch.tensor(json.load(f))
    
    print("Knowledge base changed or no cache found. Generating embeddings...")
    with open(vault_filepath, 'r', encoding='utf-8') as vault_file:
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

# Sparse Context Selection
def sparse_context_selection(rewritten_input, vault_embeddings, vault_content, min_k=1, max_k=5, threshold=0.8):
    if vault_embeddings.nelement() == 0:
        return []

    input_embedding = ollama.embeddings(model='mxbai-embed-large', prompt=rewritten_input)["embedding"]
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings)
    
    valid_indices = torch.where(cos_scores >= threshold)[0].tolist()
    if len(valid_indices) < min_k:
        top_indices = torch.topk(cos_scores, k=min_k)[1].tolist()
    else:
        sorted_valid_indices = sorted(valid_indices, key=lambda i: cos_scores[i], reverse=True)
        top_indices = sorted_valid_indices[:max_k]

    selected_contexts = [vault_content[idx].strip() for idx in top_indices]
    print(f"Selected {len(selected_contexts)} contexts using SCS.")
    return selected_contexts

# Rewrite query
def rewrite_query(user_input_json, conversation_history, ollama_model, client):
    user_input = json.loads(user_input_json)["Query"]
    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])
    prompt = f"""Rewrite the following query by incorporating relevant context from the conversation history.
    Return ONLY the rewritten query text.
    Conversation History: {context}
    Original query: [{user_input}]
    Rewritten query: """
    
    response = client.chat.completions.create(
        model=ollama_model,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=200,
        n=1,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()

# Main chat function
def ollama_chat(user_input, system_message, vault_embeddings, vault_content, ollama_model, conversation_history, client):
    conversation_history.append({"role": "user", "content": user_input})
    rewritten_query = user_input

    relevant_context = sparse_context_selection(rewritten_query, vault_embeddings, vault_content)
    if relevant_context:
        context_str = "\n".join(relevant_context)
        print("Context Pulled from Documents:\n" + CYAN + context_str + RESET_COLOR)
    else:
        print(CYAN + "No relevant context found." + RESET_COLOR)
    
    user_input_with_context = f"{user_input}\n\nRelevant Context:\n{context_str}" if relevant_context else user_input
    conversation_history[-1]["content"] = user_input_with_context

    messages = [{"role": "system", "content": system_message}, *conversation_history]
    response = client.chat.completions.create(
        model=ollama_model,
        messages=messages,
        max_tokens=2000,
    )
    return response.choices[0].message.content

# Parse arguments and initialize client
parser = argparse.ArgumentParser(description="Ollama Chat")
parser.add_argument("--model", default="llama3", help="Ollama model to use")
args = parser.parse_args()

print(NEON_GREEN + "Initializing Ollama API client..." + RESET_COLOR)
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='llama3'
)

# Load knowledge base and questions
vault_filepath = "Knowledge Base.txt"
vault_embeddings_tensor = load_or_generate_embeddings(vault_filepath)
with open(vault_filepath, 'r', encoding='utf-8') as f:
    vault_content = f.readlines()

question_file = "question.txt"
if os.path.exists(question_file):
    with open(question_file, 'r', encoding='utf-8') as q_file:
        questions = [line.strip() for line in q_file if line.strip()]
    answers = []
    for question in questions:
        response = ollama_chat(question, "You are a helpful assistant.", vault_embeddings_tensor, vault_content, args.model, [], client)
        answers.append({"Question": question, "Answer": response})
    
    with open("answers.txt", "w", encoding="utf-8") as f:
        for item in answers:
            f.write(f"Question: {item['Question']}\nAnswer: {item['Answer']}\n\n")
else:
    print(YELLOW + "No questions found in question.txt. Exiting..." + RESET_COLOR)
