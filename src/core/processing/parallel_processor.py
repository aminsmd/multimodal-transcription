#!/usr/bin/env python3
"""
Parallel processing functionality for the transcription pipeline.

This module handles parallel processing of video chunks and other tasks.
"""

import concurrent.futures
from typing import List, Callable, Any, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed


class ParallelProcessor:
    """
    Handles parallel processing of tasks.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the parallel processor.
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
    
    def process_chunks_parallel(self, chunks: List[Dict], process_func: Callable, **kwargs) -> List[Dict]:
        """
        Process chunks in parallel using the provided function.
        
        Args:
            chunks: List of chunk information dictionaries
            process_func: Function to process each chunk
            **kwargs: Additional arguments to pass to process_func
            
        Returns:
            List of results from processing each chunk
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_chunk = {}
            for chunk_info in chunks:
                future = executor.submit(process_func, chunk_info, **kwargs)
                future_to_chunk[future] = chunk_info
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                try:
                    result = future.result()
                    results.append({
                        "chunk_info": chunk_info,
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    print(f"Error processing chunk {chunk_info.get('start_time', 'unknown')}-{chunk_info.get('end_time', 'unknown')}: {str(e)}")
                    results.append({
                        "chunk_info": chunk_info,
                        "result": {"error": str(e)},
                        "success": False
                    })
        
        return results
    
    def process_tasks_parallel(self, tasks: List[Callable], *args, **kwargs) -> List[Any]:
        """
        Process a list of tasks in parallel.
        
        Args:
            tasks: List of callable tasks
            *args: Arguments to pass to each task
            **kwargs: Keyword arguments to pass to each task
            
        Returns:
            List of results from each task
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(task, *args, **kwargs) for task in tasks]
            
            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error in parallel task: {str(e)}")
                    results.append({"error": str(e)})
        
        return results
    
    def map_parallel(self, func: Callable, items: List[Any], *args, **kwargs) -> List[Any]:
        """
        Apply a function to a list of items in parallel.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            *args: Additional arguments to pass to func
            **kwargs: Keyword arguments to pass to func
            
        Returns:
            List of results
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {}
            for item in items:
                future = executor.submit(func, item, *args, **kwargs)
                future_to_item[future] = item
            
            # Collect results in order
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error processing item {item}: {str(e)}")
                    results.append({"error": str(e), "item": item})
        
        return results
