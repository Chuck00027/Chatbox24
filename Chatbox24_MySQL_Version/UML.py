from graphviz import Digraph

# Create a UML class diagram
uml = Digraph('UML_Diagram', format='png')

# Define classes and their attributes/methods based on the provided Python files
classes = {
    "ChatbotLauncher": {
        "attributes": ["root"],
        "methods": ["setup_ui()", "run_script(script_name)"]
    },
    "PDFProcessor": {
        "attributes": ["root", "pdf_label", "text_input", "save_button"],
        "methods": ["setup_ui()", "drop_handler(event)", "process_pdf(file_path)", "split_text_into_chunks(text, max_chunk_size)", "save_text()"]
    },
    "TestingProcessor": {
        "attributes": ["root", "vault_filepath", "vault_embeddings_tensor", "vault_content"],
        "methods": ["setup_ui()", "compute_file_hash(filepath)", "load_vault_content()", "load_or_generate_embeddings(embedding_model)", "sparse_context_selection(input_text, threshold, max_k)", "generate_rag_response(user_input)", "calculate_semantic_similarity(text1, text2, model)", "process_eml_file(file_path)", "process_files_batch(file_paths)", "display_response(response)", "on_drop(event)"]
    },
    "TrainingProcessor": {
        "attributes": ["root"],
        "methods": ["setup_ui()", "on_drop(event)", "process_files_batch(file_paths)", "process_eml_file(file_path)", "analyze_and_process_text(input_text, ollama_model)", "clean_input_text(input_text)", "extract_json_from_content(content)", "update_progress(subject)", "display_response(response)"]
    },
    "EmailProcessor": {
        "attributes": ["root", "email_data", "vault_filepath", "vault_embeddings_tensor", "vault_content"],
        "methods": ["setup_ui()", "compute_file_hash(filepath)", "load_vault_content()", "load_or_generate_embeddings(embedding_model)", "sparse_context_selection(rewritten_input, min_k, max_k, threshold)", "generate_response(user_input)", "process_eml_file(file_path)", "on_drop(event)", "display_response(event)", "copy_to_clipboard()"]
    }
}

# Add classes to the diagram
for class_name, details in classes.items():
    label = f"{class_name}|" + "\\l".join(details["attributes"]) + "|\\l".join(details["methods"]) + "\\l"
    uml.node(class_name, label=label, shape="record")

# Define relationships (based on function calls in the provided scripts)
relationships = [
    ("ChatbotLauncher", "PDFProcessor", "Launches"),
    ("ChatbotLauncher", "TestingProcessor", "Launches"),
    ("ChatbotLauncher", "TrainingProcessor", "Launches"),
    ("ChatbotLauncher", "EmailProcessor", "Launches"),
    ("TestingProcessor", "EmailProcessor", "Uses"),
    ("TrainingProcessor", "EmailProcessor", "Uses")
]

# Add relationships to the diagram
for parent, child, label in relationships:
    uml.edge(parent, child, label=label)

# Render UML Diagram
uml_path = "/mnt/data/uml_diagram.png"
uml.render(uml_path, format='png', cleanup=True)

# Display UML Diagram
uml_path
