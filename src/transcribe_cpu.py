#!/usr/bin/env python3
"""
CPU-only transcription wrapper to avoid RTX 5090 CUDA compatibility issues.
This sets CUDA_VISIBLE_DEVICES="" before any imports.
"""
import os
import sys
import logging

# Force CPU-only execution before any CUDA initialization
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Configure logging to suppress CUDA-related warnings
logging.getLogger('nemo_logger').setLevel(logging.ERROR)
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)

# Suppress specific NUMA and CUDA warnings
import warnings
warnings.filterwarnings('ignore', message='.*CUDA.*')
warnings.filterwarnings('ignore', message='.*conditional node support.*')

# Now import the transcription functionality
from transcribe import transcribe_audio, format_text_into_paragraphs

# Make the functions available when this module is imported
__all__ = ['transcribe_audio', 'format_text_into_paragraphs']

if __name__ == '__main__':
    # If run directly, behave like transcribe.py
    if len(sys.argv) < 2:
        print("Usage: python transcribe_cpu.py <audio_filepath>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    transcribed_text = transcribe_audio(audio_file)
    
    # Format the text into paragraphs
    formatted_text = format_text_into_paragraphs(transcribed_text)
    
    # Ensure output directory exists
    OUTPUT_DIR = "assets/output"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save the transcribed text to a Markdown file
    output_filename = os.path.join(OUTPUT_DIR, os.path.splitext(os.path.basename(audio_file))[0] + '.md')
    with open(output_filename, 'w') as f:
        f.write(f"# Transcription of {os.path.basename(audio_file)}\n\n")
        f.write(formatted_text)
    
    print(f"Transcription complete. Text saved to {output_filename}")
