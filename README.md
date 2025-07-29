# Summyt

Summyt is a Python-based tool that automates the process of downloading, transcribing, and summarizing YouTube videos. It leverages the NeMo toolkit for accurate speech-to-text transcription and a local language model for generating concise summaries.

## Features

- **YouTube Video Processing:** Downloads audio from YouTube videos for local processing.
- **GPU-Accelerated Transcription:** Utilizes NVIDIA's NeMo toolkit for fast and accurate transcription, with automatic fallback to CPU if a compatible GPU is not available.
- **Memory Optimization:** Employs audio chunking to manage memory consumption effectively, even with long videos.
- **Local Summarization:** Connects to a local language model (e.g., via LM Studio) to generate summaries of the transcribed text.
- **Customizable Configuration:** Allows for easy customization of model settings, file paths, and prompts through a simple `config.ini` file.

## Project Structure

- `src/`: Contains the core application logic.
- `assets/`: Stores input and output files.
- `docs/`: Contains project documentation, including the LICENSE.
- `requirements.txt`: Lists project dependencies.
- `README.md`: This file.

## Setup

1.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

2.  **Activate the virtual environment:**

    - On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    - On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install PyTorch with CUDA support (Recommended):**

    Before installing other dependencies, it is highly recommended to install PyTorch with support for your specific CUDA version. You can find the correct command for your system on the [PyTorch website](https://pytorch.org/get-started/locally/).

    For example, to install PyTorch with CUDA 12.9 support, you would run:

    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129
    ```

4.  **Install other dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Before running the application, you need to configure the `src/config.ini` file:

```ini
[youtubedl]

yt-dlp-format="yt-dlp -x --audio-format wav"
tts-model="nvidia/parakeet-tdt-0.6b-v2"
provider-url="http://localhost:1234/v1/chat/completions"
llm="google/gemma-3n-e4b"
summarization-prompt="Create a concise summary of the following audio transcript..."
summary-save-path="C:\Path\To\Your\Summaries"
transcribed-text-save-path="C:\Path\To\Your\Transcripts"
max-summary-length=100000
```

- **`provider-url`**: The URL of your local language model server (e.g., LM Studio).
- **`llm`**: The name of the language model to use for summarization.
- **`summary-save-path`**: The directory where the generated summaries will be saved.
- **`transcribed-text-save-path`**: The directory where the transcribed text will be saved.

## Usage

### Command-Line Interface (CLI)

To run the main summarization script from the command line, use the following command:

```bash
python src/summyt.py <youtube_url>
```

Replace `<youtube_url>` with the URL of the YouTube video you want to process.

### Web Interface

To use the web interface, first start the web server:

- On Windows:
    ```bash
    src\run_server.bat
    ```
- On macOS and Linux:
    ```bash
    bash src/run_server.sh
    ```

Once the server is running, open your web browser and navigate to `http://127.0.0.1:5000`.

(Note: `run_server.sh` is not yet created, but `run_transcribe.sh` is available for direct transcription.)


## Dependencies

- torch
- torchvision
- torchaudio
- yt-dlp
- librosa
- soundfile
- nemo_toolkit[asr]
- requests
- configparser
- matplotlib
- scipy
- nltk
