from flask import Flask, request, jsonify, render_template
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import summyt

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize_endpoint():
    data = request.get_json()
    youtube_url = data.get('url')

    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    try:
        summary, processing_time = summyt.process_video(youtube_url)
        return jsonify({'summary': summary, 'processing_time': processing_time})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
