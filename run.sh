#!/bin/bash

# Audio Processor Docker Run Script
# Usage: ./run.sh <input_directory> <output_directory> [book_id]

INPUT_DIR=${1:-/tmp/input}
OUTPUT_DIR=${2:-/tmp/output}
BOOK_ID=${3:-}

echo "Starting audio processing..."
echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Book ID: $BOOK_ID"

# Create directories if they don't exist
mkdir -p "$INPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Build the Docker image
echo "Building Docker image..."
docker build -t audio-processor .

# Run the container
CMD="docker run --rm \
  -v $INPUT_DIR:/input \
  -v $OUTPUT_DIR:/output \
  audio-processor \
  --input-dir /input \
  --output-file /output/output.mp3"

if [ -n "$BOOK_ID" ]; then
  CMD="$CMD --book-id $BOOK_ID"
fi

echo "Running command: $CMD"
eval $CMD

echo "Audio processing completed!"
