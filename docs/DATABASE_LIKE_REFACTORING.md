# Database-like Refactoring Summary

## Overview

The transcription pipeline has been refactored to use a database-like interface for video management, making it more compatible with future database deployments on AWS. This refactoring introduces a repository pattern that abstracts file system operations behind a database-like interface.

## Key Changes

### 1. VideoRepository Class (`src/storage/video_repository.py`)

**Purpose**: Acts as a database-like interface for video management.

**Key Features**:
- Video lookup by ID (primary key)
- Video lookup by file hash (unique constraint)
- Video lookup by filename (indexed field)
- Status tracking and metadata management
- Search and filtering capabilities
- Automatic file validation

**Database-like Operations**:
```python
# Primary key lookup
video = repository.find_by_id("video_123")

# Unique constraint lookup
video = repository.find_by_hash("sha256_hash")

# Indexed field lookup
video = repository.find_by_filename("video.mp4")

# Query with filters (WHERE clause equivalent)
videos = repository.list_all(status="transcribed")

# Count operation
count = repository.count(status="pending")
```

### 2. VideoEntity Model

**Purpose**: Represents video records with database-like structure.

**Key Fields**:
- `video_id`: Primary key
- `file_hash`: Unique identifier for deduplication
- `status`: Processing status (pending, processing, transcribed, error)
- `metadata`: Additional database-compatible fields
- `created_at`, `updated_at`: Timestamps for audit trails

**Database Compatibility**:
- Serializable to/from JSON
- Status tracking and updates
- Metadata storage
- Audit trail support

### 3. Enhanced TranscriptionConfig

**New Database-compatible Fields**:
- `video_id`: Video ID for database lookups
- `file_managed`: Whether file is managed by repository
- `original_input`: Original input before resolution

**New Methods**:
- `from_video_entity()`: Create config from VideoEntity
- Enhanced serialization for database storage

### 4. Updated TranscriptionPipeline

**New Features**:
- Video resolution using repository
- Database-like video lookup
- Automatic video entity management
- Status tracking and updates

**New Parameters**:
- `enable_video_repository`: Enable database-like interface
- Enhanced video resolution logic

## Usage Examples

### 1. Basic Video Lookup

```python
# Initialize repository
repository = VideoRepository("data")

# Lookup video by ID (database-like)
video = repository.find_by_id("Adam_2024-03-03_6_32_PM")
if video:
    print(f"Found video: {video.filename}")
    print(f"Status: {video.status}")
    print(f"Path: {video.file_path}")
```

### 2. Pipeline with Repository

```python
# Initialize pipeline with repository
pipeline = TranscriptionPipeline(
    base_dir="outputs",
    data_dir="data",
    enable_video_repository=True
)

# Process video by ID (database-like)
config = TranscriptionConfig(
    video_input="Adam_2024-03-03_6_32_PM",  # Video ID instead of path
    chunk_duration=300
)

results = pipeline.process_video(config)
```

### 3. Database-like Operations

```python
# Search videos
results = repository.search("Adam", field="filename")

# Filter by status
processed_videos = repository.list_all(status="transcribed")

# Update video status
video.update_status("processing", run_id="run_123")
repository.save(video)
```

## Benefits

### 1. Database Compatibility
- Video lookup by ID instead of file paths
- Structured data models
- Status tracking and metadata
- Easy transition to real database

### 2. Future-proof for AWS
- Repository pattern compatible with ORMs
- Structured data models for database mapping
- Status tracking for workflow management
- Metadata storage for additional fields

### 3. Improved Developer Experience
- Consistent interface for video operations
- Automatic file resolution and validation
- Status tracking and audit trails
- Search and filtering capabilities

## Migration Path to Real Database

### 1. Current Implementation
- File-based storage with JSON metadata
- In-memory caching for performance
- Repository pattern for abstraction

### 2. Future Database Integration
- Replace file storage with database queries
- Use ORM (SQLAlchemy, Django ORM) for VideoEntity
- Implement database-specific repository
- Add database migrations and schema management

### 3. AWS Deployment Ready
- Repository pattern works with AWS RDS
- Structured models compatible with database schemas
- Status tracking for workflow management
- Metadata storage for additional fields

## Testing

The refactoring includes comprehensive tests:

```bash
# Run integration tests
python test_database_integration.py

# Run example usage
python examples/database_like_usage.py
```

## Command Line Usage

The pipeline now supports database-like operations:

```bash
# Process video by ID (database-like)
python src/transcription_pipeline_new.py --input "video_id" --data-dir "data"

# Disable repository if needed
python src/transcription_pipeline_new.py --input "video_id" --no-video-repository
```

## Files Modified

1. **New Files**:
   - `src/storage/video_repository.py`: VideoRepository and VideoEntity
   - `examples/database_like_usage.py`: Usage examples
   - `test_database_integration.py`: Integration tests
   - `DATABASE_LIKE_REFACTORING.md`: This documentation

2. **Modified Files**:
   - `src/models.py`: Added database-compatible fields
   - `src/core/pipeline.py`: Integrated VideoRepository
   - `src/transcription_pipeline_new.py`: Added repository support
   - `src/storage/__init__.py`: Added VideoRepository exports

## Conclusion

The refactoring successfully introduces a database-like interface while maintaining backward compatibility. The system is now more suitable for future database deployment on AWS, with clear migration paths and improved developer experience.

Key improvements:
- ✅ Database-like video lookup by ID
- ✅ Repository pattern for abstraction
- ✅ Database-compatible data models
- ✅ Status tracking and metadata
- ✅ Future-proof for AWS deployment
- ✅ Comprehensive testing and examples
