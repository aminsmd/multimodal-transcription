# Organized Python File Structure

This document describes the new organized structure of the transcription pipeline codebase.

## 📁 Directory Structure

```
src/
├── 📁 core/                    # Core pipeline components
│   └── file_manager.py        # Enhanced file management system
├── 📁 data/                    # Data management utilities
│   ├── data_setup.py          # Data directory setup and management
│   └── setup_data.py          # Quick setup script
├── 📁 utils/                   # Utility functions
│   ├── __init__.py            # Utility module exports
│   ├── video_utils.py         # Video processing utilities
│   ├── file_utils.py          # File handling utilities
│   └── config_utils.py        # Configuration utilities
├── models.py                   # Data models and configuration classes
└── transcription_pipeline.py  # Main transcription pipeline
```

## 🔧 Core Components

### **1. File Manager (`core/file_manager.py`)**
Enhanced file management system with automatic organization:

```python
from core.file_manager import create_file_manager

# Initialize file manager
file_manager = create_file_manager("data", auto_organize=True)

# Add video (automatically organized)
video_info = file_manager.add_video("path/to/video.mp4")

# Resolve video path (by ID, filename, or path)
resolved_path, is_new = file_manager.resolve_video_path("video_id")

# Get video information
video_info = file_manager.get_video_info("video_id")

# Update status
file_manager.update_video_status("video_id", "transcribed")
```

### **2. Data Management (`data/`)**
Complete data directory management:

```python
from data.data_setup import DataManager

# Initialize data manager
dm = DataManager("data")

# Add videos with automatic organization
video_info = dm.add_video("video.mp4", organize_by_date=True)

# List and filter videos
videos = dm.list_videos(status="raw")

# Organize by type
dm.organize_by_type({
    "lectures": ["video_id_1", "video_id_2"],
    "discussions": ["video_id_3"]
})
```

### **3. Utility Functions (`utils/`)**
Common utility functions:

```python
from utils import get_video_duration, validate_video_file, format_timestamp

# Video utilities
duration = get_video_duration("video.mp4")
is_valid, error = validate_video_file("video.mp4")
timestamp = format_timestamp(125.5)  # "02:05.500"

# File utilities
from utils.file_utils import get_file_hash, create_safe_filename
file_hash = get_file_hash("video.mp4")
safe_name = create_safe_filename("video:file.mp4")  # "video_file.mp4"

# Configuration utilities
from utils.config_utils import load_config, save_config
config = load_config("config.json")
save_config(config, "new_config.json")
```

## 🚀 Enhanced Pipeline Usage

### **Automatic File Management**
The pipeline now automatically manages video files:

```python
from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig

# Initialize with file management
pipeline = TranscriptionPipeline(
    base_dir="outputs",
    data_dir="data",
    enable_file_management=True
)

# Process video (automatically resolves path)
config = TranscriptionConfig(
    video_input="video_id_or_path",  # Can be ID, filename, or path
    chunk_duration=300,
    max_workers=4
)

results = pipeline.process_video(config)
```

### **Command Line with File Management**
```bash
# Enable file management (default)
python src/transcription_pipeline.py --input video.mp4 --data-dir data

# Disable file management
python src/transcription_pipeline.py --input video.mp4 --no-file-management

# Custom data directory
python src/transcription_pipeline.py --input video.mp4 --data-dir my_data
```

## 📊 File Management Features

### **Automatic Organization**
- **By Date**: Videos organized by creation/upload date
- **By Type**: Videos categorized by content type
- **By Project**: Videos grouped by project or course

### **Smart Path Resolution**
The system can resolve videos by:
- **Full Path**: `/path/to/video.mp4`
- **Video ID**: `lecture_math_abc123`
- **Filename**: `lecture.mp4`
- **Partial Match**: `lecture` (finds first match)

### **Deduplication**
- **File Hash**: Automatic detection of duplicate files
- **Smart Copying**: Only copy if not already managed
- **Registry**: Fast lookup of managed files

### **Status Tracking**
- **Raw**: Newly added videos
- **Processed**: Videos that have been processed
- **Transcribed**: Videos with completed transcripts
- **Error**: Videos that failed processing

## 🔄 Integration Examples

### **1. Basic Usage with File Management**
```python
from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig

# Initialize pipeline with file management
pipeline = TranscriptionPipeline(
    base_dir="outputs",
    data_dir="data",
    enable_file_management=True
)

# Process video (system handles file management)
config = TranscriptionConfig(
    video_input="lecture.mp4",  # Will be automatically resolved
    chunk_duration=300,
    max_workers=4
)

results = pipeline.process_video(config)
```

### **2. Batch Processing**
```python
# Get all raw videos
file_manager = pipeline.file_manager
raw_videos = file_manager.list_videos(status="raw")

# Process each video
for video in raw_videos:
    config = TranscriptionConfig(
        video_input=video['video_id'],
        chunk_duration=300,
        max_workers=4
    )
    
    results = pipeline.process_video(config)
    print(f"Processed: {results.video_id}")
```

### **3. File Organization**
```python
# Organize videos by type
file_manager.organize_videos({
    "lectures": ["video_id_1", "video_id_2"],
    "discussions": ["video_id_3"],
    "presentations": ["video_id_4"]
})

# Export video list
csv_file = file_manager.export_video_list()
```

## 📈 Benefits of New Structure

### **1. Modularity**
- **Separation of Concerns**: Each module has a specific purpose
- **Reusability**: Components can be used independently
- **Maintainability**: Easier to update and debug

### **2. File Management**
- **Automatic Organization**: No manual file management needed
- **Smart Resolution**: Works with paths, IDs, or filenames
- **Deduplication**: Prevents duplicate processing
- **Status Tracking**: Know the state of every video

### **3. Enhanced Pipeline**
- **Integrated Management**: File management built into pipeline
- **Automatic Validation**: Videos validated before processing
- **Status Updates**: Automatic status tracking
- **Error Handling**: Better error management

### **4. Developer Experience**
- **Type Safety**: Full type hints throughout
- **Documentation**: Comprehensive docstrings
- **Examples**: Multiple usage examples
- **Utilities**: Common functions readily available

## 🛠️ Migration Guide

### **From Old Structure**
```python
# Old way
pipeline = TranscriptionPipeline("outputs")
results = pipeline.process_video("video.mp4", 300, 4)

# New way
pipeline = TranscriptionPipeline("outputs", "data", enable_file_management=True)
config = TranscriptionConfig(video_input="video.mp4", chunk_duration=300, max_workers=4)
results = pipeline.process_video(config)
```

### **File Management Integration**
```python
# Old way - manual file handling
video_path = "path/to/video.mp4"
# ... manual processing ...

# New way - automatic file management
config = TranscriptionConfig(video_input="video.mp4")  # Auto-resolved
results = pipeline.process_video(config)  # Auto-managed
```

## 📚 Usage Examples

See the examples directory for comprehensive usage examples:
- `examples/enhanced_usage.py` - Complete file management demonstration
- `examples/data_management_example.py` - Data management examples
- `examples/basic_usage.py` - Basic usage with new structure

## 🎯 Next Steps

1. **Set up data directory**: `python src/data/setup_data.py`
2. **Add your videos**: Use the file management system
3. **Process videos**: Use the enhanced pipeline
4. **Organize results**: Use the built-in organization features

This new structure provides a robust, scalable foundation for video transcription with automatic file management! 🚀
