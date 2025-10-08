#!/usr/bin/env python3
"""
Test script for the new modular transcription pipeline structure.

This script tests the basic functionality of the new modular components
without requiring actual video processing.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from core.pipeline import TranscriptionPipeline
        from core.chunking import VideoChunker, ChunkProcessor
        from core.transcription import TranscriptAnalyzer, TranscriptCombiner, TranscriptFormatter
        from core.processing import ParallelProcessor, ResultProcessor
        print("✓ Core modules imported successfully")
        
        # Test AI imports
        from ai import GeminiClient, PromptManager, ModelHandler
        print("✓ AI modules imported successfully")
        
        # Test storage imports
        from storage import CacheManager, FileStorage, UploadManager
        print("✓ Storage modules imported successfully")
        
        # Test models
        from models import TranscriptionConfig, ModelType
        print("✓ Models imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_component_initialization():
    """Test that components can be initialized."""
    print("\nTesting component initialization...")
    
    try:
        from core.pipeline import TranscriptionPipeline
        from models import TranscriptionConfig
        
        # Test pipeline initialization
        pipeline = TranscriptionPipeline(base_dir="test_outputs", enable_file_management=False)
        print("✓ Pipeline initialized successfully")
        
        # Test configuration creation
        config = TranscriptionConfig(
            video_input="test_video.mp4",
            chunk_duration=300,
            max_workers=2
        )
        print("✓ Configuration created successfully")
        
        # Test component access
        assert pipeline.model_handler is not None
        assert pipeline.cache_manager is not None
        assert pipeline.file_storage is not None
        print("✓ All components accessible")
        
        return True
        
    except Exception as e:
        print(f"✗ Component initialization error: {e}")
        return False

def test_model_handler():
    """Test the model handler functionality."""
    print("\nTesting model handler...")
    
    try:
        from ai.model_handler import ModelHandler
        from models import ModelType
        
        handler = ModelHandler()
        
        # Test model info
        info = handler.get_model_info()
        assert "name" in info
        assert "description" in info
        print("✓ Model handler info retrieved")
        
        # Test model validation
        validation = handler.validate_model_choice(ModelType.GEMINI_2_5_PRO, 100.0)
        assert "valid" in validation
        print("✓ Model validation working")
        
        return True
        
    except Exception as e:
        print(f"✗ Model handler error: {e}")
        return False

def test_prompt_manager():
    """Test the prompt manager functionality."""
    print("\nTesting prompt manager...")
    
    try:
        from ai.prompt_manager import PromptManager
        
        manager = PromptManager()
        
        # Test prompt generation
        prompt = manager.get_transcript_prompt(video_duration=600, chunk_start=0, chunk_end=300)
        assert len(prompt) > 0
        assert "SEGMENT INFORMATION" in prompt
        print("✓ Prompt generation working")
        
        # Test prompt info
        info = manager.get_prompt_info()
        assert "prompt_file_path" in info
        print("✓ Prompt info retrieved")
        
        return True
        
    except Exception as e:
        print(f"✗ Prompt manager error: {e}")
        return False

def test_cache_manager():
    """Test the cache manager functionality."""
    print("\nTesting cache manager...")
    
    try:
        from storage.cache_manager import CacheManager
        from models import TranscriptionConfig
        from pathlib import Path
        
        # Create test cache directory
        test_cache_dir = Path("test_cache")
        test_cache_dir.mkdir(exist_ok=True)
        
        manager = CacheManager(Path("test_outputs"), test_cache_dir)
        
        # Test configuration hash
        config = TranscriptionConfig(video_input="test.mp4", chunk_duration=300)
        config_hash = manager.get_config_hash(config)
        assert len(config_hash) > 0
        print("✓ Configuration hash generated")
        
        # Test cache stats
        stats = manager.get_cache_stats()
        assert "total_cached_transcripts" in stats
        print("✓ Cache stats retrieved")
        
        # Clean up
        import shutil
        shutil.rmtree(test_cache_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"✗ Cache manager error: {e}")
        return False

def test_file_storage():
    """Test the file storage functionality."""
    print("\nTesting file storage...")
    
    try:
        from storage.file_storage import FileStorage
        from pathlib import Path
        
        # Create test storage directory
        test_storage_dir = Path("test_storage")
        test_storage_dir.mkdir(exist_ok=True)
        
        storage = FileStorage(test_storage_dir)
        
        # Test storage stats
        stats = storage.get_storage_stats()
        assert "total_videos" in stats
        assert "total_transcripts" in stats
        print("✓ Storage stats retrieved")
        
        # Test video listing
        videos = storage.list_videos()
        assert isinstance(videos, list)
        print("✓ Video listing working")
        
        # Clean up
        import shutil
        shutil.rmtree(test_storage_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"✗ File storage error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Modular Transcription Pipeline Structure")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_component_initialization,
        test_model_handler,
        test_prompt_manager,
        test_cache_manager,
        test_file_storage
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The modular structure is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
