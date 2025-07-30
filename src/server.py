from flask import Flask, request, jsonify, render_template, Response
import sys
import os
import json
import configparser

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import summyt
from download import get_video_info

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info_endpoint():
    data = request.get_json()
    youtube_url = data.get('url')

    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    info = get_video_info(youtube_url)
    if info:
        return jsonify({'title': info.get('title'), 'description': info.get('description')})
    else:
        return jsonify({'error': 'Failed to get video info'}), 500

@app.route('/summarize', methods=['POST'])
def summarize_endpoint():
    data = request.get_json()
    youtube_url = data.get('url')
    enable_hashtag = data.get('enable_hashtag', True)

    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    def generate():
        for progress_update in summyt.process_video(youtube_url, enable_hashtag):
            yield f"data: {json.dumps(progress_update)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/summarize_with_category', methods=['POST'])
def summarize_with_category_endpoint():
    data = request.get_json()
    youtube_url = data.get('url')
    enable_hashtag = data.get('enable_hashtag', True)
    enforced_category = data.get('enforced_category')

    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    def generate():
        for progress_update in summyt.process_video(youtube_url, enable_hashtag, enforced_category=enforced_category):
            yield f"data: {json.dumps(progress_update)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/get_config')
def get_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    with open(config_path, 'r') as f:
        config_content = f.read()
    return Response(config_content, mimetype='text/plain')

@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.get_json()
    new_config = data.get('config')
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    try:
        with open(config_path, 'w') as f:
            f.write(new_config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_llm_providers')
def get_llm_providers():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config.read(config_path)
    selected_provider = config['youtubedl'].get('llm_provider', 'lmstudio').strip('"')
    current_llm_model = config['youtubedl'].get('llm', '').strip('"')
    print(f"get_llm_providers: selected_provider={selected_provider}")
    print(f"get_llm_providers: providers={['lmstudio', 'ollama']}")
    print(f"get_llm_providers: current_llm_model={current_llm_model}")
    return jsonify({'providers': ['lmstudio', 'ollama'], 'selected': selected_provider, 'current_llm_model': current_llm_model})

@app.route('/update_llm_provider', methods=['POST'])
def update_llm_provider():
    data = request.get_json()
    new_provider = data.get('provider')
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config.read(config_path)
    config['youtubedl']['llm_provider'] = f'"{new_provider}"'
    try:
        with open(config_path, 'w') as f:
            config.write(f)
        print(f"update_llm_provider: new_provider={new_provider}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"update_llm_provider: error={e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_categories')
def get_categories():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config.read(config_path)
    summary_save_path = config['youtubedl'].get('summary-save-path', '').strip('"')
    print(f"get_categories: summary_save_path={summary_save_path}")
    if not summary_save_path or not os.path.isdir(summary_save_path):
        print("get_categories: summary_save_path is not valid or does not exist")
        return jsonify({'categories': []})
    
    try:
        categories = [d for d in os.listdir(summary_save_path) if os.path.isdir(os.path.join(summary_save_path, d))]
        print(f"get_categories: categories={categories}")
        return jsonify({'categories': categories})
    except Exception as e:
        print(f"get_categories: error={e}")
        return jsonify({'categories': [], 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)