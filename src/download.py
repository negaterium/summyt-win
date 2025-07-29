import configparser
import sys
import yt_dlp
import os
import librosa
import soundfile as sf

DOWNLOAD_DIR = "assets/input"

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

def get_video_info(url):
    """Gets video information (title, etc.) without downloading the video."""
    try:
        ydl_opts_info = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if info_dict is None:
                print(f"Error: Could not get information for URL: {url}")
                return None
            return info_dict
    except Exception as e:
        print(f"Error getting video information: {e}")
        return None

def download_youtube(url):
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        info_dict = get_video_info(url)
        if info_dict is None:
            sys.exit(1)
            
        video_title = info_dict.get('title', 'unknown_title')
        
        # Sanitize video_title for use as a filename
        sanitized_video_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        # Check for existing transcript file in the new transcribed-text-save-path
        expected_transcript_filepath = os.path.join(TRANSCRIBED_OUTPUT_DIR, f"{sanitized_video_title}.md")
        if os.path.exists(expected_transcript_filepath):
            print(f"Transcript for '{video_title}' already exists at '{expected_transcript_filepath}'. Skipping download and transcription.")
            return expected_transcript_filepath, video_title, True # Added a flag for existing transcript

        # If transcript not found, check for existing audio file
        # Use ydl.prepare_filename to get the exact filename yt-dlp would generate
        ydl_opts_filename = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts_filename) as ydl:
            base_filepath_without_ext = os.path.splitext(ydl.prepare_filename(info_dict))[0]
        expected_mono_filepath = f"{base_filepath_without_ext}_mono.wav"

        if os.path.exists(expected_mono_filepath):
            print(f"Warning: Audio file '{expected_mono_filepath}' already exists. Skipping download.")
            return expected_mono_filepath, video_title, False # Flag indicates no existing transcript

        ydl_opts = {
            'format': 'bestaudio/best',
            'overwrites': False, 
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            downloaded_info_dict = ydl.extract_info(url, download=True)
            filepath = downloaded_info_dict['requested_downloads'][0]['filepath']

        print(f"Downloaded: {filepath}")

        # Convert to mono
        audio, sr = librosa.load(filepath, sr=None, mono=True)
        mono_filepath = os.path.splitext(filepath)[0] + "_mono.wav"
        sf.write(mono_filepath, audio, sr)
        print(f"Converted to mono: {mono_filepath}")

        print("Download and conversion completed successfully.")
        return mono_filepath, video_title, False # Flag indicates no existing transcript
    except Exception as e:
        print(f"An error occurred during download: {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python download.py <youtube_url>")
        sys.exit(1)
    video_url = sys.argv[1]
    download_youtube(video_url)
