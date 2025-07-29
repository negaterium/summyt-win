import os
import sys
import logging
import torch
import nltk
import nemo.collections.asr as nemo_asr
import librosa
import soundfile as sf
import tempfile
import shutil

# Configure logging for clear output
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
# Suppress excessive logging from NeMo and PyTorch Lightning
logging.getLogger('nemo_logger').setLevel(logging.ERROR)
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)

# OUTPUT_DIR will be loaded from config.ini in summyt.py and passed here

def _check_gpu_compatibility() -> bool:
    """
    Checks for a compatible NVIDIA GPU and ensures CUDA operations are working.
    Returns True if a compatible GPU is found, False otherwise.
    """
    if not torch.cuda.is_available():
        logging.info("NVIDIA GPU not available or CUDA is not set up.")
        return False

    try:
        device_properties = torch.cuda.get_device_properties(0)
        capability = f"sm_{device_properties.major}{device_properties.minor}"
        supported_archs = torch.cuda.get_arch_list()

        logging.info(f"Detected GPU: {device_properties.name} (CUDA Capability: {capability})")

        if capability not in supported_archs:
            logging.warning(f"GPU architecture '{capability}' is not in the supported list by this PyTorch build.")
            logging.warning(f"Supported architectures: {supported_archs}")
            return False

        # Perform a quick test to confirm CUDA is operational
        test_tensor = torch.randn(1, 1).cuda()
        _ = test_tensor + test_tensor
        logging.info("GPU is compatible and CUDA operations are working.")
        return True

    except Exception as e:
        logging.error(f"GPU compatibility check failed with an error: {e}")
        return False

def _create_audio_chunks(audio_filepath: str, chunk_duration_s: int = 30) -> list[str]:
    """
    Splits an audio file into smaller chunks of a specified duration.

    Args:
        audio_filepath: Path to the audio file.
        chunk_duration_s: The duration of each chunk in seconds.

    Returns:
        A list of filepaths to the created audio chunks.
    """
    try:
        audio, sr = librosa.load(audio_filepath, sr=None, mono=True)
        chunk_samples = chunk_duration_s * sr
        num_chunks = len(audio) // chunk_samples + (1 if len(audio) % chunk_samples > 0 else 0)

        temp_dir = tempfile.mkdtemp()
        chunk_paths = []

        for i in range(num_chunks):
            start_sample = i * chunk_samples
            end_sample = start_sample + chunk_samples
            chunk_audio = audio[start_sample:end_sample]
            chunk_filename = os.path.join(temp_dir, f"chunk_{i}.wav")
            sf.write(chunk_filename, chunk_audio, sr)
            chunk_paths.append(chunk_filename)
        
        return chunk_paths

    except Exception as e:
        logging.error(f"Failed to create audio chunks: {e}")
        return []

def _perform_transcription(audio_filepath: str, device: str) -> str:
    """
    Performs audio transcription using the specified device ('cuda' or 'cpu').

    Args:
        audio_filepath: Path to the audio file.
        device: The compute device to use ('cuda' or 'cpu').

    Returns:
        The transcribed text, or an empty string if transcription fails.
    """
    logging.info(f"Loading Parakeet model for transcription on {device.upper()}...")
    try:
        # Load the pre-trained EncDecRNNTBPEModel
        asr_model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v2")
        asr_model.to(device) 

        logging.info("Creating audio chunks to manage memory...")
        audio_chunks = _create_audio_chunks(audio_filepath)
        if not audio_chunks:
            return ""

        logging.info(f"Starting transcription on {device.upper()}...")
        full_transcription = ""
        for chunk_path in audio_chunks:
            transcriptions = asr_model.transcribe(audio=[chunk_path], batch_size=1)
            if transcriptions and transcriptions[0]:
                full_transcription += transcriptions[0].text + " "

        # Clean up temporary chunk files
        shutil.rmtree(os.path.dirname(audio_chunks[0]))

        logging.info(f"Transcription on {device.upper()} completed successfully.")
        return full_transcription.strip()

    except Exception as e:
        logging.error(f"An error occurred during transcription on {device.upper()}: {e}")
        # Clean up memory if a CUDA error occurs
        if 'cuda' in device.lower() and torch.cuda.is_available():
            torch.cuda.empty_cache()
        raise  # Re-raise the exception to be caught by the calling function

def _ensure_nltk_data():
    """
    Ensure NLTK 'punkt' tokenizer is downloaded.
    """
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        logging.info("NLTK 'punkt' not found. Downloading...")
        nltk.download('punkt', quiet=True)

def format_text_into_paragraphs(text: str, sentences_per_paragraph: int = 5) -> str:
    """
    Formats a long string of text into paragraphs.
    """
    if not text.strip():
        return ""
    _ensure_nltk_data()
    sentences = nltk.sent_tokenize(text)
    paragraphs = [" ".join(sentences[i:i+sentences_per_paragraph]) 
                  for i in range(0, len(sentences), sentences_per_paragraph)]
    return "\n\n".join(paragraphs)

def transcribe_audio(audio_filepath: str, video_title: str, transcribed_output_dir: str) -> str:
    """
    Transcribes an audio file, attempting GPU first and falling back to CPU.
    Saves the transcribed text to a Markdown file in the specified output directory.

    Args:
        audio_filepath: The path to the audio file to transcribe.
        video_title: The title of the video, used for naming the output file.
        transcribed_output_dir: The directory where the transcribed text will be saved.

    Returns:
        The transcribed text.
    """
    transcribed_text = None

    # Attempt transcription on GPU if compatible
    if _check_gpu_compatibility():
        try:
            transcribed_text = _perform_transcription(audio_filepath, 'cuda')
        except Exception as e:
            logging.warning(f"GPU transcription failed. Falling back to CPU. Error: {e}")
    else:
        logging.info("Proceeding with CPU for transcription.")

    # Fallback to CPU if GPU is not compatible or failed
    if transcribed_text is None:
        try:
            transcribed_text = _perform_transcription(audio_filepath, 'cpu')
        except Exception as e:
            logging.critical(f"CPU transcription also failed. Error: {e}")
            return ""  # Return empty string on critical failure

    if transcribed_text:
        logging.info("Formatting transcribed text into paragraphs.")
        formatted_text = format_text_into_paragraphs(transcribed_text)

        # Sanitize video_title for use as a filename
        sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_filename = os.path.join(transcribed_output_dir, f"{sanitized_title}.md")

        os.makedirs(transcribed_output_dir, exist_ok=True)
        
        logging.info(f"Saving transcription to {output_filename}")
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(f"# Transcription of {video_title}\n\n")
                f.write(formatted_text)
            logging.info("Transcription saved.")
        except IOError as e:
            logging.error(f"Failed to write to file {output_filename}: {e}")
            # Do not exit, just log the error, as transcription itself might have succeeded

        # Delete all .wav files from the input directory after successful transcription
        try:
            # Extract the directory from the audio_filepath
            input_directory = os.path.dirname(audio_filepath)
            if not input_directory:
                input_directory = "."  # Use current directory if no path is specified
                
            # Find all .wav files in the input directory
            wav_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.wav')]
            
            if wav_files:
                logging.info(f"Found {len(wav_files)} .wav file(s) in {input_directory}")
                deleted_count = 0
                for filename in wav_files:
                    file_path = os.path.join(input_directory, filename)
                    try:
                        os.remove(file_path)
                        logging.info(f"Deleted .wav file: {file_path}")
                        deleted_count += 1
                    except Exception as e:
                        logging.error(f"Failed to delete file {file_path}: {e}")
                
                logging.info(f"Successfully deleted {deleted_count} of {len(wav_files)} .wav files")
            else:
                logging.info(f"No .wav files found in {input_directory}")
        except Exception as e:
            logging.error(f"Failed to process .wav files in directory {input_directory}: {e}")
    else:
        logging.error("Transcription resulted in empty text. No output file will be created.")
        
    return transcribed_text

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python transcribe.py <audio_filepath> <video_title> [output_directory]")
        sys.exit(1)

    audio_file = sys.argv[1]
    video_title = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "assets/output"

    if not os.path.exists(audio_file):
        logging.error(f"Audio file not found: {audio_file}")
        sys.exit(1)

    logging.info(f"Starting transcription for: {audio_file}")
    transcribed_text = transcribe_audio(audio_file, video_title, output_dir)

    if transcribed_text:
        print("Transcription process completed.")
    else:
        print("Transcription process failed.")