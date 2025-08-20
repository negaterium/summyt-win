import sys
import os
import configparser
import json
import shutil
import requests
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load configuration
def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    config.read(config_path)
    
    llm_provider = config['youtubedl'].get('llm_provider', 'lmstudio').strip('"')
    summary_save_path = config['youtubedl']['summary-save-path'].strip('"')
    category_save_path = summary_save_path  # Use summary-save-path for categories
    llm_model = config['youtubedl'].get('llm')
    
    if llm_provider == 'ollama':
        provider_url = config['youtubedl'].get('ollama_api_url')
    elif llm_provider == 'openrouter':
        provider_url = config['youtubedl'].get('openrouter-api-url')
    else: # Default to lmstudio
        provider_url = config['youtubedl'].get('provider-url')

    if not llm_model or not provider_url:
        print("Error: Missing required configuration values (llm, provider-url, or ollama_api_url)")
        sys.exit(1)
        
    openrouter_api_key = config['youtubedl'].get('openrouter-api-key', '').strip('"')
        
    return llm_provider, llm_model.strip('"'), provider_url.strip('"'), summary_save_path, category_save_path, openrouter_api_key

LLM_PROVIDER, MODEL_NAME, API_URL, SUMMARY_OUTPUT_DIR, CATEGORY_OUTPUT_DIR, OPENROUTER_API_KEY = load_config()

def analyze_with_llm(text, prompt):
    """
    Analyze text using the same LLM used in summarization.
    """
    headers = {}
    if LLM_PROVIDER == 'openrouter':
        headers['Authorization'] = f'Bearer {OPENROUTER_API_KEY}'
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n---\n\n{text}",
                }
            ],
        }
    elif LLM_PROVIDER == 'ollama':
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n---\n\n{text}",
                }
            ],
            "stream": False
        }
    else: # Default to lmstudio
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n---\n\n{text}",
                }
            ],
        }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if LLM_PROVIDER == 'ollama':
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"]
        else: # lmstudio or openrouter
            if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
                return data["choices"][0]["message"]["content"]

        print(f"Unexpected API response format: {json.dumps(data, indent=2)}")
        return ""
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        if e.response:
            print(f"LM Studio Response: {e.response.text}")
        print(f"Please ensure the model '{MODEL_NAME}' is loaded in your LLM provider and that the server is running correctly at {API_URL}.")
        return ""
        
    except Exception as e:
        print(f"An unexpected error occurred during analysis: {e}")
        return ""

def categorize_summary(summary_filepath):
    """
    Categorize a summary file by analyzing its content and moving it to the appropriate folder.
    """
    # Check if the file exists
    if not os.path.exists(summary_filepath):
        print(f"Error: Summary file not found at {summary_filepath}")
        return False
    
    # Read the summary file
    try:
        with open(summary_filepath, 'r', encoding='utf-8') as f:
            summary_content = f.read()
    except Exception as e:
        print(f"Error reading summary file: {e}")
        return False
    
    # Extract the title from the filename
    filename = os.path.basename(summary_filepath)
    title_part = filename.replace('-summarized.md', '')
    
    # Create a prompt for categorization
    prompt = f"""
    Analyze the following summary and assign it to one of the following categories:
    - Technology
    - Health & Wellness
    - Finance & Business
    - Education & Learning
    - Entertainment & Arts
    - Science & Nature
    - Lifestyle & Hobbies
    - News & Politics
    - Other

    Provide only the category name from the list above. Do not include any other text or explanation.

    Summary:
    {summary_content}

    Category:
    """
    
    # Analyze the content using the LLM
    category = analyze_with_llm(summary_content, prompt).strip()
    
    # If no category was determined, use the title
    if not category:
        category = title_part
    
    # Create the category directory if it doesn't exist
    category_dir = os.path.join(CATEGORY_OUTPUT_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    
    # Create the new filename with the category
    new_filename = f"{title_part}-summarized.md"
    new_filepath = os.path.join(category_dir, new_filename)
    
    # Move the file to the category directory
    try:
        shutil.move(summary_filepath, new_filepath)
        print(f"Summary categorized as '{category}' and moved to {new_filepath}")
        return True
    except Exception as e:
        print(f"Error moving file: {e}")
        return False

def main():
    """
    Main function to categorize a summary file.
    Usage: python categorize.py <summary_filepath>
    """
    if len(sys.argv) < 2:
        print("Usage: python categorize.py <summary_filepath>")
        sys.exit(1)
    
    summary_filepath = sys.argv[1]
    success = categorize_summary(summary_filepath)
    
    if success:
        print("Categorization completed successfully.")
    else:
        print("Categorization failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()
