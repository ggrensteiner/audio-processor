#!/usr/bin/env python3
"""
Audio Processor Script
Concatenates MP3 files, normalizes loudness, applies noise filter using ffmpeg, and handles chapter markers.
Downloads metadata from Hardcover API.
"""

import os
import subprocess
import argparse
import requests
from pathlib import Path
import json
import re
import yaml


def natural_sort_key(filename):
    """Convert a filename to a tuple of string and number components for natural sorting"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(filename))]


class AudioProcessor:
    def __init__(self, input_dir, output_file, config_file="config.json"):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.config_file = Path(config_file)
        self.temp_dir = self.output_file.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Config file {self.config_file} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            print(f"Invalid YAML in config file {self.config_file}: {e}. Using defaults.")
            return {}
    
    def find_mp3_files(self):
        """Find all MP3 files in subdirectories and sort them naturally"""
        mp3_files = []
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith('.mp3'):
                    mp3_files.append(Path(root) / file)
        
        # Sort files naturally by name
        return sorted(mp3_files, key=lambda x: natural_sort_key(x.name))
    
    def get_hardcover_metadata(self, book_id):
        """Download metadata from Hardcover API"""
        try:
            # Using the Hardcover API endpoint
            api_key = self.config.get('api', {}).get('hardcover_api_key', 'YOUR_HARDCOVER_API_KEY_HERE')
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            query = """
            query GetBook($id: ID!) {
                book(id: $id) {
                    title
                    author
                    description
                    isbn
                    publicationYear
                    publisher
                }
            }
            """
            
            variables = {"id": book_id}
            
            response = requests.post(
                "https://api.hardcover.app/v1/graphql",
                json={"query": query, "variables": variables},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']['book']:
                    return data['data']['book']
                else:
                    print(f"Book not found with ID: {book_id}")
                    return None
            else:
                print(f"Failed to fetch metadata for book {book_id} (Status: {response.status_code})")
                return None
        except Exception as e:
            print(f"Error fetching metadata: {e}")
            return None
    
    def extract_chapter_markers(self, input_file):
        """Extract chapter markers from an MP3 file if they exist"""
        try:
            # Use ffprobe to check for chapter markers
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_chapters', str(input_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            chapters_data = json.loads(result.stdout)
            
            if 'chapters' in chapters_data and chapters_data['chapters']:
                return chapters_data['chapters']
            return None
        except subprocess.CalledProcessError:
            # ffprobe failed, no chapters found
            return None
        except json.JSONDecodeError:
            # Invalid JSON from ffprobe
            return None
    
    def create_chapter_markers(self, mp3_files, output_file):
        """Create chapter markers for concatenated audio file"""
        # If any source file has chapters, use those
        for mp3_file in mp3_files:
            chapters = self.extract_chapter_markers(mp3_file)
            if chapters:
                # If chapters exist, we'll use them
                return chapters
        
        # If no chapters found, create default chapter markers
        # This would typically be based on file durations or other metadata
        # For now, we'll create a simple chapter marker for each file
        total_duration = 0
        chapters = []
        
        for i, mp3_file in enumerate(mp3_files):
            # Get duration of each file
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_entries', 'format=duration',
                '-of', 'default=nw=1',
                str(mp3_file)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                # Parse ffprobe output to get duration
                duration = 0
                for line in result.stdout.split('\n'):
                    if line.startswith('duration='):
                        duration = float(line.split('=')[1])
                        break
                
                # Create chapter marker for this file
                chapters.append({
                    "id": i,
                    "start_time": total_duration,
                    "end_time": total_duration + duration,
                    "title": f"Chapter {i+1}"
                })
                
                total_duration += duration
            except Exception as e:
                print(f"Error getting duration for {mp3_file}: {e}")
                continue
        
        return chapters
    
    def embed_chapter_markers(self, input_file, output_file, chapters):
        """Embed chapter markers into the audio file"""
        if not chapters:
            return True  # No chapters to embed
        
        # Create chapter file
        chapter_file = self.temp_dir / "chapters.txt"
        with open(chapter_file, 'w') as f:
            for chapter in chapters:
                f.write(f"CHAPTER{chapter['id']}={chapter['start_time']}\n")
                f.write(f"CHAPTER{chapter['id']}NAME={chapter['title']}\n")
        
        # Embed chapters using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-i', str(chapter_file),
            '-map', '0:a',
            '-map', '1:t:0',
            '-c', 'copy',
            '-f', 'mp3',
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # Clean up chapter file
            chapter_file.unlink()
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error embedding chapters: {e}")
            # Clean up chapter file
            if chapter_file.exists():
                chapter_file.unlink()
            return False
    
    def normalize_loudness(self, input_file, output_file):
        """Normalize loudness using ffmpeg"""
        loudness_config = self.config.get('audio_processing', {}).get('loudness_normalization', {})
        i_value = loudness_config.get('I', -16)
        tp_value = loudness_config.get('TP', -1.5)
        lra_value = loudness_config.get('LRA', 11)
        
        filter_string = f"loudnorm=I={i_value}:TP={tp_value}:LRA={lra_value}:print_format=json"
        
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-af', filter_string,
            '-f', 'mp3',
            str(output_file)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error normalizing loudness: {e}")
            return False
    
    def apply_noise_filter(self, input_file, output_file):
        """Apply noise filter using ffmpeg"""
        noise_config = self.config.get('audio_processing', {}).get('noise_filter', {})
        noise_reduction = noise_config.get('noise_reduction', 0.5)
        noise_floor = noise_config.get('noise_floor', 0.3)
        noise_profile = noise_config.get('noise_profile', 0.2)
        
        filter_string = f"afftnoise={noise_reduction}:{noise_floor}:{noise_profile}"
        
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-af', filter_string,
            str(output_file)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error applying noise filter: {e}")
            return False
    
    def concatenate_mp3_files(self, mp3_files, output_file):
        """Concatenate MP3 files using ffmpeg"""
        # Create a list file for concatenation
        list_file = self.temp_dir / "file_list.txt"
        with open(list_file, 'w') as f:
            for mp3_file in mp3_files:
                f.write(f"file '{mp3_file}'\n")
        
        output_config = self.config.get('audio_processing', {}).get('output', {})
        bitrate = output_config.get('bitrate', '192k')
        
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-c:a', 'mp3',
            '-b:a', bitrate,
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # Clean up temporary file
            list_file.unlink()
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error concatenating files: {e}")
            # Clean up temporary file
            if list_file.exists():
                list_file.unlink()
            return False
    
    def process_audio_files(self):
        """Main processing function"""
        print("Finding MP3 files...")
        mp3_files = self.find_mp3_files()
        
        if not mp3_files:
            print("No MP3 files found")
            return False
            
        print(f"Found {len(mp3_files)} MP3 files")
        
        # Create a temporary file for concatenation
        temp_concat_file = self.temp_dir / "temp_concat.mp3"
        
        print("Concatenating MP3 files...")
        if not self.concatenate_mp3_files(mp3_files, temp_concat_file):
            print("Concatenation failed")
            return False
            
        print("Normalizing loudness...")
        temp_normalize_file = self.temp_dir / "temp_normalize.mp3"
        if not self.normalize_loudness(temp_concat_file, temp_normalize_file):
            print("Loudness normalization failed")
            return False
            
        print("Applying noise filter...")
        temp_filter_file = self.temp_dir / "temp_filter.mp3"
        if not self.apply_noise_filter(temp_normalize_file, temp_filter_file):
            print("Noise filtering failed")
            return False
            
        # Check for chapter markers and embed them if needed
        print("Handling chapter markers...")
        chapters = self.create_chapter_markers(mp3_files, temp_filter_file)
        if chapters:
            # Embed chapter markers
            temp_chapter_file = self.temp_dir / "temp_chapter.mp3"
            if not self.embed_chapter_markers(temp_filter_file, temp_chapter_file, chapters):
                print("Failed to embed chapter markers")
                return False
            # Move final file to output location
            temp_chapter_file.rename(self.output_file)
        else:
            # Move final file to output location
            temp_filter_file.rename(self.output_file)
        
        # Clean up temp directory
        for file in self.temp_dir.iterdir():
            if file.is_file():
                file.unlink()
        self.temp_dir.rmdir()
        
        print(f"Processing complete. Output saved to {self.output_file}")
        return True


def main():
    parser = argparse.ArgumentParser(description='Audio Processor')
    parser.add_argument('--input-dir', required=True, help='Directory containing MP3 files in subfolders')
    parser.add_argument('--output-file', required=True, help='Output file path')
    parser.add_argument('--book-id', help='Hardcover book ID for metadata (optional)')
    parser.add_argument('--config-file', default='config.yaml', help='Path to config file')
    
    args = parser.parse_args()
    
    processor = AudioProcessor(args.input_dir, args.output_file, args.config_file)
    
    if args.book_id:
        print(f"Fetching metadata for book ID: {args.book_id}")
        metadata = processor.get_hardcover_metadata(args.book_id)
        if metadata:
            print("Metadata retrieved successfully")
            # Save metadata to a file
            metadata_file = Path(args.output_file).parent / f"{Path(args.output_file).stem}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"Metadata saved to {metadata_file}")
    
    print("Starting audio processing...")
    success = processor.process_audio_files()
    
    if success:
        print("Audio processing completed successfully")
    else:
        print("Audio processing failed")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
