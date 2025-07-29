import sys
import os
import configparser

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import download
import summarize

try:
    import transcribe
except ImportError:
    print("Warning: nemo-toolkit[asr] not found. Transcription will not work.")
    transcribe = None

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
    return summary_save_path, transcribed_text_save_path

SUMMARY_OUTPUT_DIR, TRANSCRIBED_OUTPUT_DIR = load_config()

def main():
    if len(sys.argv) < 2:
        print("Usage: python summyt.py <youtube_url>")
        sys.exit(1)
    
    youtube_url = sys.argv[1]

    # Get video info early to construct expected summary filename
    info_dict = download.get_video_info(youtube_url)
    if info_dict is None:
        sys.exit(1)
    video_title = info_dict.get('title', 'unknown_title')

    # Sanitize video_title for use as a filename
    sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    expected_summary_filepath = os.path.join(SUMMARY_OUTPUT_DIR, f"{sanitized_title}-summarized.md")

    if os.path.exists(expected_summary_filepath):
        print(f"Summary for '{video_title}' already exists at '{expected_summary_filepath}'. Skipping all steps.")
        sys.exit(0)

    transcribed_text = ""
    print("Proceeding with audio download and local transcription.")
    print(f"Downloading audio from {youtube_url}...")
    downloaded_filepath, video_title, is_transcript_existing = download.download_youtube(youtube_url)

    if downloaded_filepath is None:
        sys.exit(1)

    if is_transcript_existing:
        print(f"Using existing transcript from: {downloaded_filepath}")
        try:
            with open(downloaded_filepath, 'r', encoding='utf-8') as f:
                # Skip the first two lines (title and empty line)
                f.readline()
                f.readline()
                transcribed_text = f.read()
        except FileNotFoundError:
            print(f"Error: Existing transcript file not found at {downloaded_filepath}. Exiting.")
            sys.exit(1)
    else:
        print(f"Processing audio file: {downloaded_filepath}")
        if transcribe:
            print("Transcribing audio...")
            # Pass video_title and TRANSCRIBED_OUTPUT_DIR to transcribe_audio
            transcribed_text = transcribe.transcribe_audio(downloaded_filepath, video_title, TRANSCRIBED_OUTPUT_DIR)
            if not transcribed_text.strip():
                print("Transcription failed or produced empty text. Exiting.")
                sys.exit(1)
            print("Transcription complete.")
        else:
            print("Skipping transcription due to missing nemo-toolkit[asr]. Exiting.")
            sys.exit(1)

    print("Summarizing text...")
    summarized_text = summarize.summarize_text(transcribed_text)

    if not summarized_text.strip():
        print("Summarization failed or produced empty text. Exiting without saving summary.")
        sys.exit(1)

    print("Summarization complete.")

    # Sanitize video_title for use as a filename
    sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_filename = os.path.join(SUMMARY_OUTPUT_DIR, f"{sanitized_title}-summarized.md")

    try:
        os.makedirs(SUMMARY_OUTPUT_DIR, exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Summary of {video_title}\n\n")
            f.write(summarized_text)
        print(f"Summary saved to {output_filename}")
    except IOError as e:
        print(f"Failed to write summary to {output_filename}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
