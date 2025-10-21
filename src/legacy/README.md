# Legacy Code Directory

This directory contains legacy code that has been replaced by newer, more modular implementations.

## Files in this directory:

### `transcription_pipeline.py`
- **Status**: LEGACY - Replaced by modular implementation
- **Size**: 1,443 lines
- **Last Modified**: Oct 7, 18:41
- **Replaced by**: `src/core/pipeline.py` (accessed via `src/transcription_pipeline.py`)
- **Reason for deprecation**: Monolithic file that was refactored into modular components

## Migration Notes:

The old `transcription_pipeline.py` has been replaced by:
1. `src/core/pipeline.py` - The main modular pipeline implementation
2. `src/transcription_pipeline.py` - Entry point that uses the modular implementation

## Usage:

If you need to reference the old implementation for any reason, it's available in this directory. However, the new modular implementation in `src/core/pipeline.py` is the recommended approach.

## Breaking Changes:

- The old `TranscriptionPipeline` class has been refactored
- File structure has been modularized
- Some method signatures may have changed
- New features like video repository and enhanced file management are available in the new version
