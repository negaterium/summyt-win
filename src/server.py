from flask import Flask, request, jsonify, render_template, Response
import sys
import os
import json

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

    def generate():
        for progress_update in summyt.process_video(youtube_url):
            yield f"data: {json.dumps(progress_update)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
