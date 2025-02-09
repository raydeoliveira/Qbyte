"""
RNG Device Manager
================

This module provides a unified interface for managing and reading from RNG
(Random Number Generator) devices, supporting both physical TrueRNG hardware
and mock devices for testing.

Key Features:
------------
1. Unified interface for different RNG sources
2. Automatic device detection and initialization
3. Concurrent reading from multiple devices
4. Support for TurboRNG high-speed mode
5. Clean resource management
6. Comprehensive error handling and logging

Device Types:
-----------
1. TrueRNG: Physical USB random number generator
2. TurboRNG: High-speed version of TrueRNG
3. Mock RNG: Software simulation for testing
4. PRNG: Pseudo-random number generator

Usage:
------
1. Basic usage:
   ```python
   manager = RNGManager()
   try:
       manager.initialize_devices()
       data, turbo_data = manager.read_data()
       # Process data...
   finally:
       manager.cleanup()
   ```

2. Configuration:
   ```python
   from config import RNGConfig
   RNGConfig.SOURCE = 'trng'  # Use physical devices
   RNGConfig.NUM_DEVICES = 8  # Number of devices to use
   ```

Error Handling:
-------------
The module includes comprehensive error handling for:
- Device initialization failures
- Read timeouts
- Communication errors
- Resource cleanup issues

All errors are logged with appropriate context for debugging.
"""

import logging
import serial
from serial.tools import list_ports
from typing import List, Optional, Tuple
from config import RNGConfig
from mock_rng import create_mock_reader, MockRNGReader

logger = logging.getLogger(__name__)

class RNGManager:
    """
    Manages RNG device initialization, reading, and cleanup.
    
    This class provides a unified interface for working with different types
    of RNG devices. It handles device discovery, initialization, concurrent
    reading, and proper resource cleanup.
    
    Features:
    - Automatic device discovery and initialization
    - Support for multiple device types (TrueRNG, Mock, PRNG)
    - Thread-safe concurrent reading
    - Proper resource management
    
    Example:
        manager = RNGManager()
        try:
            if manager.initialize_devices():
                data, turbo = manager.read_data()
                # Process data...
        finally:
            manager.cleanup()
    """
    def __init__(self):
        """
        Initialize the RNG manager.
        
        Sets up internal state for device management but does not
        initialize devices. Call initialize_devices() to set up
        the actual devices.
        """
        self.mock_reader: Optional[MockRNGReader] = None
        self.serial_devices: List[serial.Serial] = []
        self.turbo_device: Optional[serial.Serial] = None
        
    def initialize_devices(self) -> bool:
        """
        Initialize RNG devices based on configuration.
        
        This method:
        1. Checks the configured RNG source type
        2. Discovers and initializes appropriate devices
        3. Sets up reading mechanisms
        
        The initialization process varies by device type:
        - TRNG: Discovers and opens serial ports
        - Mock: Creates mock device instances
        - PRNG: No initialization needed
        
        Returns:
            bool: True if initialization successful, False otherwise
        
        Raises:
            RuntimeError: If device initialization fails critically
        """
        try:
            if RNGConfig.SOURCE == 'mock':
                return self._initialize_mock_devices()
            elif RNGConfig.SOURCE == 'trng':
                return self._initialize_trng_devices()
            elif RNGConfig.SOURCE == 'prng':
                logger.info("Using PRNG source - no device initialization needed")
                return True
            else:
                logger.error(f"Unsupported RNG source: {RNGConfig.SOURCE}")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize RNG devices: {e}")
            return False
    
    def _initialize_mock_devices(self) -> bool:
        """
        Initialize mock RNG devices for testing.
        
        Creates a MockRNGReader instance configured according to current
        settings. Mock devices can operate in either random or pattern mode.
        
        Returns:
            bool: True if mock devices initialized successfully
        
        Raises:
            Exception: If mock device initialization fails
        """
        try:
            self.mock_reader = create_mock_reader(
                num_devices=RNGConfig.NUM_DEVICES,
                pattern_mode=RNGConfig.MOCK_PATTERN_MODE
            )
            logger.info(f"Initialized {RNGConfig.NUM_DEVICES} mock RNG devices")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize mock devices: {e}")
            return False
    
    def _initialize_trng_devices(self) -> bool:
        """
        Initialize physical TrueRNG devices.
        
        This method:
        1. Scans for available TrueRNG devices
        2. Identifies regular and TurboRNG devices
        3. Opens serial connections with appropriate settings
        
        The method supports both regular TrueRNG devices and the
        high-speed TurboRNG variant.
        
        Returns:
            bool: True if devices initialized successfully
        
        Raises:
            Exception: If device initialization fails
        """
        try:
            ports_available = list(list_ports.comports())
            rng_ports = []
            turbo_port = None
            
            # Find available TrueRNG devices
            for port in ports_available:
                if port[1].startswith("TrueRNG"):
                    if 'pro' in port[1]:
                        turbo_port = str(port[0])
                        logger.info(f'Found TrueRNG Pro device at {port[0]}')
                    else:
                        rng_ports.append(str(port[0]))
                        logger.info(f'Found TrueRNG device at {port[0]}')
            
            # Initialize regular TrueRNG devices
            if RNGConfig.HALO_MODE:
                for port in rng_ports[:RNGConfig.NUM_DEVICES]:
                    device = serial.Serial(
                        port=port,
                        timeout=RNGConfig.DEVICE_TIMEOUT
                    )
                    self.serial_devices.append(device)
                    logger.debug(f'Successfully opened serial port {port}')
            
            # Initialize TurboRNG if needed
            if RNGConfig.TURBO_MODE and turbo_port:
                self.turbo_device = serial.Serial(
                    port=turbo_port,
                    timeout=RNGConfig.DEVICE_TIMEOUT
                )
                logger.debug(f'Successfully opened TurboRNG port {turbo_port}')
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TrueRNG devices: {e}")
            return False
    
    def read_data(self) -> Tuple[List[bytes], Optional[bytes]]:
        """
        Read data from all initialized devices.
        
        This method reads from all available devices according to the
        current configuration. For physical devices, it reads the
        configured number of bytes from each device. For mock devices,
        it retrieves the next batch of generated data.
        
        Returns:
            Tuple[List[bytes], Optional[bytes]]: 
                - List of data chunks from regular devices
                - Data from TurboRNG device (if available)
        
        Note:
            The number of bytes read from each device is determined by
            RNGConfig.SPEED. If a read fails for any device, an empty
            bytes object is returned for that device.
        """
        if RNGConfig.SOURCE == 'mock':
            if self.mock_reader:
                data = self.mock_reader.get_data()
                # Mock devices don't support turbo mode
                return data, None
            return [], None
            
        elif RNGConfig.SOURCE == 'trng':
            regular_data = []
            turbo_data = None
            
            # Read from regular devices
            for device in self.serial_devices:
                try:
                    data = device.read(RNGConfig.SPEED)
                    regular_data.append(data)
                except Exception as e:
                    logger.error(f"Error reading from device: {e}")
                    regular_data.append(bytes())
            
            # Read from turbo device if available
            if self.turbo_device and RNGConfig.TURBO_MODE:
                try:
                    turbo_data = self.turbo_device.read(RNGConfig.SPEED)
                except Exception as e:
                    logger.error(f"Error reading from TurboRNG: {e}")
            
            return regular_data, turbo_data
            
        return [], None
    
    def cleanup(self):
        """
        Clean up all device connections and resources.
        
        This method ensures proper cleanup of all resources:
        1. Stops mock device reading threads
        2. Closes all serial port connections
        3. Releases system resources
        
        This method should be called when the RNG manager is no longer
        needed or before program termination.
        """
        if self.mock_reader:
            self.mock_reader.stop_reading()
        
        for device in self.serial_devices:
            try:
                device.close()
            except:
                pass
        
        if self.turbo_device:
            try:
                self.turbo_device.close()
            except:
                pass 