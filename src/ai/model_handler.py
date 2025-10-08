#!/usr/bin/env python3
"""
Model handling for the transcription pipeline.

This module manages different AI models and their configurations.
"""

from typing import Dict, List, Optional
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ModelType


class ModelHandler:
    """
    Handles different AI models for transcription.
    """
    
    def __init__(self, default_model: ModelType = ModelType.GEMINI_2_5_PRO):
        """
        Initialize the model handler.
        
        Args:
            default_model: Default model to use
        """
        self.default_model = default_model
        self.current_model = default_model
        self.model_configs = self._initialize_model_configs()
    
    def _initialize_model_configs(self) -> Dict[ModelType, Dict]:
        """
        Initialize model configurations.
        
        Returns:
            Dictionary of model configurations
        """
        return {
            ModelType.GEMINI_2_5_PRO: {
                "name": "Gemini 2.5 Pro",
                "description": "Latest Gemini model with multimodal capabilities",
                "max_file_size_mb": 1000,
                "supports_video": True,
                "supports_audio": True,
                "api_endpoint": "models/gemini-2.5-pro",
                "recommended_for": ["high_quality_transcription", "multimodal_analysis"]
            },
            ModelType.GEMINI_1_5_PRO: {
                "name": "Gemini 1.5 Pro",
                "description": "Previous generation Gemini model",
                "max_file_size_mb": 500,
                "supports_video": True,
                "supports_audio": True,
                "api_endpoint": "models/gemini-1.5-pro",
                "recommended_for": ["standard_transcription", "cost_effective"]
            }
        }
    
    def set_model(self, model: ModelType):
        """
        Set the current model.
        
        Args:
            model: Model type to use
        """
        if model not in self.model_configs:
            raise ValueError(f"Unsupported model: {model}")
        
        self.current_model = model
        print(f"Model set to: {self.model_configs[model]['name']}")
    
    def get_model_config(self, model: Optional[ModelType] = None) -> Dict:
        """
        Get configuration for a model.
        
        Args:
            model: Model type (uses current model if None)
            
        Returns:
            Model configuration dictionary
        """
        if model is None:
            model = self.current_model
        
        return self.model_configs.get(model, {})
    
    def get_available_models(self) -> List[ModelType]:
        """
        Get list of available models.
        
        Returns:
            List of available model types
        """
        return list(self.model_configs.keys())
    
    def get_model_info(self, model: Optional[ModelType] = None) -> Dict:
        """
        Get detailed information about a model.
        
        Args:
            model: Model type (uses current model if None)
            
        Returns:
            Model information dictionary
        """
        if model is None:
            model = self.current_model
        
        config = self.get_model_config(model)
        return {
            "model_type": model.value,
            "name": config.get("name", "Unknown"),
            "description": config.get("description", ""),
            "max_file_size_mb": config.get("max_file_size_mb", 0),
            "supports_video": config.get("supports_video", False),
            "supports_audio": config.get("supports_audio", False),
            "api_endpoint": config.get("api_endpoint", ""),
            "recommended_for": config.get("recommended_for", [])
        }
    
    def is_model_suitable_for_file(self, file_size_mb: float, model: Optional[ModelType] = None) -> bool:
        """
        Check if a model is suitable for a file of given size.
        
        Args:
            file_size_mb: File size in MB
            model: Model type (uses current model if None)
            
        Returns:
            True if model is suitable, False otherwise
        """
        config = self.get_model_config(model)
        max_size = config.get("max_file_size_mb", 0)
        return file_size_mb <= max_size
    
    def get_recommended_model(self, file_size_mb: float, requirements: List[str] = None) -> ModelType:
        """
        Get recommended model based on file size and requirements.
        
        Args:
            file_size_mb: File size in MB
            requirements: List of requirements (e.g., ["high_quality_transcription"])
            
        Returns:
            Recommended model type
        """
        if requirements is None:
            requirements = []
        
        # Filter models by file size
        suitable_models = [
            model for model in self.get_available_models()
            if self.is_model_suitable_for_file(file_size_mb, model)
        ]
        
        if not suitable_models:
            # If no model can handle the file size, return the one with largest capacity
            return max(self.get_available_models(), 
                      key=lambda m: self.get_model_config(m).get("max_file_size_mb", 0))
        
        # If no specific requirements, return the first suitable model
        if not requirements:
            return suitable_models[0]
        
        # Find model that best matches requirements
        best_model = suitable_models[0]
        best_score = 0
        
        for model in suitable_models:
            config = self.get_model_config(model)
            model_recommendations = config.get("recommended_for", [])
            
            # Calculate score based on how many requirements are met
            score = sum(1 for req in requirements if req in model_recommendations)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        return best_model
    
    def validate_model_choice(self, model: ModelType, file_size_mb: float) -> Dict[str, any]:
        """
        Validate a model choice for a given file.
        
        Args:
            model: Model type to validate
            file_size_mb: File size in MB
            
        Returns:
            Validation results dictionary
        """
        config = self.get_model_config(model)
        
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check file size
        max_size = config.get("max_file_size_mb", 0)
        if file_size_mb > max_size:
            validation["valid"] = False
            validation["errors"].append(f"File size ({file_size_mb:.1f}MB) exceeds model limit ({max_size}MB)")
        elif file_size_mb > max_size * 0.8:  # Warning at 80% of limit
            validation["warnings"].append(f"File size ({file_size_mb:.1f}MB) is close to model limit ({max_size}MB)")
        
        # Check video support
        if not config.get("supports_video", False):
            validation["warnings"].append("Model may not have optimal video support")
        
        return validation
