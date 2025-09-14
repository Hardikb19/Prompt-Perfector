import os

from promptperfector.logic.logger import log_debug

def list_available_models(models_dir):
    """
    Returns a list of (model_name, model_path) for each subfolder in models_dir containing at least one .gguf file.
    """
    # Add detailed logging to list all modules found
    log_debug(f"Listing models in directory: {models_dir}")
    if not os.path.isdir(models_dir):
        return []
    models = []
    for sub in os.listdir(models_dir):
        log_debug(f"Found subdirectory: {sub}")
        sub_path = os.path.join(models_dir, sub)
        log_debug(f"Checking subdirectory: {sub_path}")
        if os.path.isdir(sub_path):
            log_debug(f"Found model directory: {sub_path}")
            log_debug(f"Contents of {sub_path}: {os.listdir(sub_path)}")
            gguf_files = [f for f in os.listdir(sub_path) if f.lower().endswith('.gguf')]
            if gguf_files:
                first_gguf = gguf_files[0]
                full_path = os.path.join(sub_path, first_gguf)
                models.append((sub, full_path))
    return models
