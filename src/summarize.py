import sys
import os
import requests
import configparser
import json

# Summary output directory will be loaded from config.ini
# Maximum text length for summarization will be loaded from config.ini

def load_config():
    config = configparser.ConfigParser()
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

        config.read(config_path)
        if 'youtubedl' not in config:
            raise KeyError("Section 'youtubedl' not found in the configuration file.")

        llm_model = config['youtubedl'].get('llm')
        if not llm_model:
            raise KeyError("Key 'llm' not found or is empty under section 'youtubedl'.")

        provider_url = config['youtubedl'].get('provider-url')
        if not provider_url:
            raise KeyError("Key 'provider-url' not found or is empty under section 'youtubedl'.")

        summarization_prompt = config['youtubedl'].get('summarization-prompt', '')
        if not summarization_prompt:
            print("Warning: No summarization-prompt found in configuration. Using default prompt.")
            summarization_prompt = "Provide a concise summary of the following transcript. Focus on the main topics and key conclusions. Present the summary as a short paragraph."

        # Load summary save path from config
        summary_save_path = config['youtubedl'].get('summary-save-path', 'assets/output').strip('"')

        # Load max text length from config
        try:
            max_text_length = int(config['youtubedl'].get('max-summary-length', '150000'))
        except (ValueError, TypeError):
            print("Warning: Invalid value for max-summary-length in configuration. Using default value of 150000.")
            max_text_length = 150000

        return llm_model.strip('"'), provider_url.strip('"'), summarization_prompt.strip('"'), summary_save_path, max_text_length
    except Exception as e:
        print(f"An error occurred while loading the configuration: {e}")
        sys.exit(1)

MODEL_NAME, LMSTUDIO_API_URL, SUMMARIZATION_PROMPT, OUTPUT_DIR, MAX_TEXT_LENGTH = load_config()

def summarize_text(text):
    if not text.strip():
        print("Input text is empty. Skipping summarization.")
        return ""

    # Truncate text if it exceeds the maximum length
    if len(text) > MAX_TEXT_LENGTH:
        print(f"Warning: Input text is too long ({len(text)} characters). Truncating to {MAX_TEXT_LENGTH} characters.")
        text = text[:MAX_TEXT_LENGTH]

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": f"{SUMMARIZATION_PROMPT}\n\n---\n\n{text}",
            }
        ],
    }

    print(f"Sending payload to LM Studio at {LMSTUDIO_API_URL} for model: {MODEL_NAME}")


    try:
        response = requests.post(LMSTUDIO_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
            return data["choices"][0]["message"]["content"]
        else:
            print(f"Unexpected API response format: {json.dumps(data, indent=2)}")
            return ""

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        if e.response:
            print(f"LM Studio Response: {e.response.text}")
        print(f"Please ensure the model '{MODEL_NAME}' is loaded in LM Studio and that the server is running correctly at {LMSTUDIO_API_URL}.")

        return ""
    except Exception as e:
        print(f"An unexpected error occurred during summarization: {e}")
        return ""

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python summarize.py <input_filename>")
        sys.exit(1)

    input_filepath = sys.argv[1]

    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            input_text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {input_filepath}")
        sys.exit(1)

    summarized_text = summarize_text(input_text)

    if not summarized_text.strip():
        print("Summarization failed or produced an empty result.")
        sys.exit(1)

    # Removed file saving logic from here, as it's now handled by summyt.py
    print("Summarization complete.")
    print(summarized_text) # Print to stdout for testing purposes if run directly
