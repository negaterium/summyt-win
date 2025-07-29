import sys
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

def get_youtube_video_id(youtube_url: str) -> str | None:
    """
    Extracts the YouTube video ID from a given URL.
    """
    if "v=" in youtube_url:
        return youtube_url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in youtube_url:
        return youtube_url.split("youtu.be/")[1].split("&")[0]
    return None

def get_youtube_transcript(youtube_url: str) -> str | None:
    """
    Attempts to retrieve the full transcript for a YouTube video.
    Returns the transcript as a single string if successful, None otherwise.
    """
    video_id = get_youtube_video_id(youtube_url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {youtube_url}")
        return None

    try:
        # Try to get the English transcript first
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en', 'en-US'])
        
        # Fetch the actual transcript data
        transcript_data = transcript.fetch()
        
        full_transcript = " ".join([entry['text'] for entry in transcript_data])
        print(f"Successfully retrieved YouTube transcript for video ID: {video_id}")
        return full_transcript
    except NoTranscriptFound:
        print(f"No transcript found for video ID: {video_id}.")
        return None
    except TranscriptsDisabled:
        print(f"Transcripts are disabled for video ID: {video_id}.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching transcript for video ID {video_id}: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python youtube_transcript.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    transcript = get_youtube_transcript(url)
    if transcript:
        print("\n-- Retrieved Transcript --\n")
        print(transcript[:500] + "...") # Print first 500 chars
    else:
        print("Failed to retrieve transcript.")