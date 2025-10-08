# Audio Processor

A Dockerized Python script that concatenates MP3 files, normalizes loudness, applies noise filtering using ffmpeg, and handles chapter markers. It also downloads metadata from Hardcover API.

![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)

## Features

- Concatenates MP3 files from subdirectories
- Normalizes audio loudness using ffmpeg's loudnorm filter
- Applies noise reduction filter using ffmpeg's afftnoise filter
- Handles chapter markers (retrieves from source files or creates new ones)
- Downloads metadata from Hardcover API

## Requirements

- Docker
- ffmpeg
- Python 3.9+

## Installation

1. Clone this repository
2. Build the Docker image:
   ```bash
   docker build -t audio-processor .
   ```

## Usage

```bash
docker run --rm \
  -v /path/to/input/directory:/input \
  -v /path/to/output/directory:/output \
  audio-processor \
  --input-dir /input \
  --output-file /output/output.mp3
  --book-id 12345
```

### Arguments

- `--input-dir`: Directory containing MP3 files in subfolders (required)
- `--output-file`: Output file path (required)
- `--book-id`: Hardcover book ID for metadata (optional)
- `--config-file`: Path to config file (optional, defaults to config.yaml)

## How It Works

1. **Finding MP3 files**: The script recursively searches the input directory for all MP3 files
2. **Concatenation**: Uses ffmpeg's concat demuxer to combine all MP3 files
3. **Loudness Normalization**: Applies ffmpeg's loudnorm filter to normalize audio loudness
4. **Noise Filtering**: Applies ffmpeg's afftnoise filter to reduce background noise
5. **Chapter Marker Handling**: 
   - If source files contain chapter markers, they are preserved in the output
   - If source files don't contain chapter markers, new ones are created based on file durations
6. **Metadata Retrieval**: Attempts to fetch metadata from Hardcover API

## Docker Volume Mounts

The script expects the following volume mounts:
- `/input`: Directory containing MP3 files
- `/output`: Directory for output files

## Example

```bash
# Process audio files and save output to /output
docker run --rm \
  -v $PWD/input:/input \
  -v $PWD/output:/output \
  audio-processor \
  --input-dir /input \
  --output-file /output/combined.mp3
```

## Configuration

The audio processor uses a `config.yaml` file to configure processing parameters. Here's an example configuration:

```yaml
api:
  hardcover_api_key: "YOUR_HARDCOVER_API_KEY_HERE"

audio_processing:
  loudness_normalization:
    I: -16
    TP: -1.5
    LRA: 11
  noise_filter:
    noise_reduction: 0.5
    noise_floor: 0.3
    noise_profile: 0.2
  output:
    bitrate: "192k"
```

## Notes

- The script creates temporary files during processing that are automatically cleaned up
- Audio normalization and noise filtering are applied to the concatenated audio file
- Hardcover API requires a valid API key to be configured in the config.yaml file
- Chapter markers are handled automatically, preserving existing markers or creating new ones when needed
