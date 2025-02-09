"""
QByte Configuration System
========================

This module provides a centralized configuration system for the QByte application,
organizing all settings into logical categories and providing type-safe access.

Key Features:
------------
1. Type-safe configuration using dataclasses
2. Logical grouping of related settings
3. Runtime configuration updates
4. Default values for all settings
5. Easy access to configuration values

Configuration Categories:
----------------------
- RNG Configuration: Settings for random number generation devices
- Visualization: Display and UI parameters
- Processing: Core algorithm parameters and thresholds
- Output: File handling and data output settings
- IPFS: Distributed storage configuration
- Paths: System paths and directories

Usage:
------
1. Access configuration values:
   ```python
   from config import RNGConfig, ProcessingConfig
   
   speed = RNGConfig.SPEED
   threshold = ProcessingConfig.COLOR_Z
   ```

2. Update runtime configuration:
   ```python
   from config import update_runtime_config
   
   update_runtime_config(session_type='auto', remarks='test_run')
   ```

3. Get configuration by key:
   ```python
   from config import get_config_value
   
   value = get_config_value('SPEED')
   ```

Runtime Updates:
--------------
Some settings can be modified during runtime using the update_runtime_config
function. These changes are temporary and will not persist between sessions.
"""

from dataclasses import dataclass
from typing import Dict, Any
import os

@dataclass
class RNGConfig:
    """
    Random Number Generation configuration parameters.
    
    Controls the behavior of both physical TrueRNG devices and mock devices
    used for testing. These settings affect data acquisition rates, device
    selection, and operating modes.
    
    Attributes:
        SPEED: Bytes per second to read from each device
        SOURCE: RNG source type ('trng', 'prng', 'mock', 'ipfs')
        HALO_MODE: Whether to use full 8-bitstream processing
        TURBO_MODE: Whether to use TurboRNG for high-speed operation
        NUM_DEVICES: Number of RNG devices to use
        DEVICE_TIMEOUT: Seconds to wait for device response
        MOCK_PATTERN_MODE: Whether mock devices use deterministic patterns
        MOCK_PATTERN_LENGTH: Length of mock device patterns
    """
    SPEED: int = 250
    SOURCE: str = 'trng'
    HALO_MODE: bool = True
    TURBO_MODE: bool = False
    NUM_DEVICES: int = 8 if HALO_MODE else 4
    DEVICE_TIMEOUT: int = 10
    
    # Mock RNG settings
    MOCK_PATTERN_MODE: bool = False
    MOCK_PATTERN_LENGTH: int = 1000

class VisualizationConfig:
    """
    Visualization and display parameters.
    
    Controls the appearance of the QByte visualization, including
    dot sizes, text formatting, and color intensities.
    
    Attributes:
        DOT_SIZE: Size of visualization dots
        WORD_SIZE: Font size for displayed text
        DEFAULT_MARKER: Matplotlib marker style
        MAX_ON: Maximum value for color intensity
    """
    DOT_SIZE: int = 4444
    WORD_SIZE: int = 36
    DEFAULT_MARKER: str = 'o'
    MAX_ON: int = 65535

class ProcessingConfig:
    """
    Core QByte processing parameters.
    
    Controls the behavior of the coherence detection algorithms and
    shape-specific processing parameters. These settings directly
    affect how events are detected and processed.
    
    Attributes:
        COLOR_Z: Z-score threshold for color change events
        ROT_Z: Z-score threshold for rotation events
        SHAPE_WEIGHTS: Shape-specific weight matrix parameters
        CONFIDENCE_INTERVAL: Statistical confidence interval
        ZOOM_CONFIDENCE: Confidence interval for zoomed view
    """
    # Z-scores for detecting significant changes
    COLOR_Z: float = 1.65
    ROT_Z: float = 1.85
    
    # Shape-specific weight matrix parameters
    SHAPE_WEIGHTS = {
        'hypercube': {'lower': 1.4, 'upper': 4.1},
        'sphere': {'lower': 1.4, 'upper': 1.42},
        'pyramid': {'lower': 0.7, 'upper': 2.1},
        'AEM': {'lower': 0.6, 'upper': 0.64},
        'star': {'lower': 1.85, 'upper': 1.95}
    }
    
    # Statistical parameters
    CONFIDENCE_INTERVAL: float = 1.96  # For 95% confidence
    ZOOM_CONFIDENCE: float = 1.65  # For zoomed view

class OutputConfig:
    """
    Output and file handling parameters.
    
    Controls how data is saved and exported, including file rotation,
    automatic operations, and image generation settings.
    
    Attributes:
        MAX_FILE_TIME: Seconds of data per output file
        AUTO_FREQ: View switch frequency in auto mode
        IMG_TIME: Image generation frequency
        MAX_WORDS: Maximum words for image prompts
    """
    MAX_FILE_TIME: int = 600
    AUTO_FREQ: int = 600
    IMG_TIME: int = 900
    MAX_WORDS: int = 3

class IPFSConfig:
    """
    IPFS-related configuration.
    
    Settings for distributed storage integration using IPFS.
    Controls how data is stored and retrieved from the IPFS network.
    
    Attributes:
        USE_ESTUARY: Whether to use Estuary for IPFS storage
        COLLECTION_ID: Estuary collection identifier
    """
    USE_ESTUARY: bool = True
    COLLECTION_ID: str = 'd0e46d0d-7e4c-4bce-8401-ee1a10b89f3d'

class PathConfig:
    """
    Path configuration.
    
    System paths and directories used by the application.
    These paths determine where files are read from and written to.
    
    Attributes:
        WORKSPACE_ROOT: Root directory of the application
        DATA_DIR: Directory for output data files
        STABLE_DIFFUSION_DIR: Path to Stable Diffusion installation
        DEFAULT_PROMPT: Default prompt for image generation
    """
    WORKSPACE_ROOT: str = os.getcwd()
    DATA_DIR: str = os.path.join(WORKSPACE_ROOT, 'dataout')
    STABLE_DIFFUSION_DIR: str = '/home/halo/halodev/stable-diffusion'
    DEFAULT_PROMPT: str = 'hypercube algorithmic language oracle'

# Runtime configuration that can be modified during execution
runtime_config = {
    'session_type': 'static',  # 'static', 'auto', or 'nye'
    'remarks': '_',
    'genome_mode': False,
    'genome_source': 'GenomeSample.txt'
}

def update_runtime_config(**kwargs):
    """
    Update runtime configuration parameters.
    
    This function allows modification of runtime settings during
    program execution. Changes are temporary and will not persist
    between sessions.
    
    Args:
        **kwargs: Key-value pairs of configuration settings to update
    
    Example:
        update_runtime_config(
            session_type='auto',
            remarks='test_run',
            genome_mode=True
        )
    """
    runtime_config.update(kwargs)

def get_config_value(key: str) -> Any:
    """
    Get a configuration value by key.
    
    Searches through all configuration classes to find the requested value.
    Returns None if the key is not found.
    
    Args:
        key: Configuration key to look up
    
    Returns:
        Any: Configuration value if found, None otherwise
    
    Example:
        speed = get_config_value('SPEED')  # Returns RNGConfig.SPEED
    """
    for config_class in [RNGConfig, VisualizationConfig, ProcessingConfig, 
                        OutputConfig, IPFSConfig, PathConfig]:
        if hasattr(config_class, key):
            return getattr(config_class, key)
    return runtime_config.get(key) 