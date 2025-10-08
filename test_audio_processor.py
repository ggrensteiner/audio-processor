#!/usr/bin/env python3
"""
Test script for Audio Processor
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from audio_processor import AudioProcessor, natural_sort_key


def test_natural_sort_key():
    """Test natural sorting of filenames"""
    # Test with numeric filenames
    filenames = ['file1.mp3', 'file10.mp3', 'file2.mp3', 'file20.mp3']
    sorted_filenames = sorted(filenames, key=natural_sort_key)
    
    # Should sort as: file1.mp3, file2.mp3, file10.mp3, file20.mp3 (not file1.mp3, file10.mp3, file2.mp3, file20.mp3)
    expected = ['file1.mp3', 'file2.mp3', 'file10.mp3', 'file20.mp3']
    assert sorted_filenames == expected, f"Expected {expected}, got {sorted_filenames}"
    print("✓ Natural sorting test passed")


def test_config_loading():
    """Test configuration loading"""
    # Create a temporary config file
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.json"
        config_data = {
            "api": {
                "hardcover_api_key": "test_key_123"
            },
            "audio_processing": {
                "loudness_normalization": {
                    "I": -14,
                    "TP": -1.0,
                    "LRA": 10
                },
                "noise_filter": {
                    "noise_reduction": 0.3,
                    "noise_floor": 0.2,
                    "noise_profile": 0.1
                },
                "output": {
                    "bitrate": "256k"
                }
            }
        }
        
        with open(config_path, 'w') as f:
            import json
            json.dump(config_data, f)
        
        # Test loading config
        processor = AudioProcessor("/tmp", "/tmp/output.mp3", str(config_path))
        assert processor.config == config_data
        print("✓ Config loading test passed")


def test_audio_processor_instantiation():
    """Test AudioProcessor instantiation"""
    processor = AudioProcessor("/tmp", "/tmp/output.mp3")
    assert processor.input_dir == Path("/tmp")
    assert processor.output_file == Path("/tmp/output.mp3")
    print("✓ AudioProcessor instantiation test passed")


def main():
    """Run all tests"""
    print("Running Audio Processor tests...")
    
    try:
        test_natural_sort_key()
        test_config_loading()
        test_audio_processor_instantiation()
        print("All tests passed!")
        return 0
    except Exception as e:
        print(f"Test failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
