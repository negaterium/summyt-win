import sys
import os
import configparser
import time
import nltk
from nltk.corpus import stopwords
from collections import Counter

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import download
import summarize
import categorize

try:
    import transcribe
except ImportError:
    print("Warning: nemo-toolkit[asr] not found. Transcription will not work.")
    transcribe = None

# Ensure NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Load configuration
def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    config.read(config_path)
    
    summary_save_path = config['youtubedl'].get('summary-save-path', 'assets/output').strip('"')
    transcribed_text_save_path = config['youtubedl'].get('transcribed-text-save-path', 'assets/output').strip('"')
    enable_categorization = config['youtubedl'].getboolean('enable-categorization', False)
    return summary_save_path, transcribed_text_save_path, enable_categorization

SUMMARY_OUTPUT_DIR, TRANSCRIBED_OUTPUT_DIR, ENABLE_CATEGORIZATION = load_config()

def _extract_keyword(text: str) -> str:
    """
    Extracts the most relevant keyword from the text.
    """
    words = nltk.word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word.isalnum() and word not in stop_words]
    
    if not filtered_words:
        return "summary"
        
    word_counts = Counter(filtered_words)
    most_common = word_counts.most_common(1)
    return most_common[0][0] if most_common else "summary"

def process_video(youtube_url, enable_hashtag=True):
    start_time = time.time()

    yield {'status': 'Getting video information...', 'progress': 5}
    # Get video info early to construct expected summary filename
    info_dict = download.get_video_info(youtube_url)
    if info_dict is None:
        raise Exception("Could not get video information.")
    video_title = info_dict.get('title', 'unknown_title')

    # Sanitize video_title for use as a filename
    sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    expected_summary_filepath = os.path.join(SUMMARY_OUTPUT_DIR, f"{sanitized_title}-summarized.md")

    if os.path.exists(expected_summary_filepath):
        yield {'status': 'Summary already exists. Reading existing summary...', 'progress': 100}
        with open(expected_summary_filepath, 'r', encoding='utf-8') as f:
            summary = f.read()
        processing_time = time.time() - start_time
        yield {'status': 'Completed', 'progress': 100, 'summary': summary, 'processing_time': f"{processing_time:.2f} seconds"}
        return

    transcribed_text = ""
    yield {'status': 'Proceeding with audio download and local transcription.', 'progress': 10}
    yield {'status': f'Downloading audio from {youtube_url}...', 'progress': 20}
    downloaded_filepath, video_title, is_transcript_existing = download.download_youtube(youtube_url)

    if downloaded_filepath is None:
        raise Exception("Failed to download audio.")

    if is_transcript_existing:
        yield {'status': f'Using existing transcript from: {downloaded_filepath}', 'progress': 40}
        try:
            with open(downloaded_filepath, 'r', encoding='utf-8') as f:
                # Skip the first two lines (title and empty line)
                f.readline()
                f.readline()
                transcribed_text = f.read()
        except FileNotFoundError:
            raise Exception(f"Existing transcript file not found at {downloaded_filepath}.")
    else:
        yield {'status': f'Processing audio file: {downloaded_filepath}', 'progress': 30}
        if transcribe:
            yield {'status': 'Transcribing audio...', 'progress': 50}
            # Pass video_title and TRANSCRIBED_OUTPUT_DIR to transcribe_audio
            transcribed_text = transcribe.transcribe_audio(downloaded_filepath, video_title, TRANSCRIBED_OUTPUT_DIR)
            if not transcribed_text.strip():
                raise Exception("Transcription failed or produced empty text.")
            yield {'status': 'Transcription complete.', 'progress': 70}
        else:
            raise Exception("Skipping transcription due to missing nemo-toolkit[asr].")

    yield {'status': 'Summarizing text...', 'progress': 80}
    summarized_text = summarize.summarize_text(transcribed_text)

    if not summarized_text.strip():
        raise Exception("Summarization failed or produced empty text.")

    yield {'status': 'Summarization complete.', 'progress': 90}

    # Extract keyword and prepend to summary if enabled
    final_summary_content = f"# Summary of {video_title}\n\n" + summarized_text
    if enable_hashtag:
        keyword = _extract_keyword(summarized_text)
        final_summary_content = f"#{keyword}\n\n" + final_summary_content

    # Sanitize video_title for use as a filename
    sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_filename = os.path.join(SUMMARY_OUTPUT_DIR, f"{sanitized_title}-summarized.md")

    try:
        os.makedirs(SUMMARY_OUTPUT_DIR, exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(final_summary_content)
        yield {'status': f'Summary saved to {output_filename}', 'progress': 95}
    except IOError as e:
        raise Exception(f"Failed to write summary to {output_filename}: {e}")

    if ENABLE_CATEGORIZATION:
        yield {'status': 'Categorizing summary...', 'progress': 98}
        categorize.categorize_summary(output_filename)

    processing_time = time.time() - start_time
    yield {'status': 'Completed', 'progress': 100, 'summary': final_summary_content, 'processing_time': f"{processing_time:.2f} seconds"}

def main():
    if len(sys.argv) < 2:
        print("Usage: python summyt.py <youtube_url>")
        sys.exit(1)
    
    youtube_url = sys.argv[1]

    try:
        # For CLI usage, we just print the final summary and time
        final_result = None
        for progress_update in process_video(youtube_url):
            if 'summary' in progress_update:
                final_result = progress_update
            print(f"Status: {progress_update['status']} (Progress: {progress_update['progress']}%) ")
        
        if final_result:
            print(f"\nSummary:\n{final_result['summary']}")
            print(f"\nProcessing time: {final_result['processing_time']}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
