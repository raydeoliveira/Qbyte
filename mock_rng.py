"""
Mock RNG Module for QByte Testing
================================

This module provides a mock implementation of TrueRNG devices for testing and development
purposes without requiring physical hardware. It supports both random and deterministic
data generation modes.

Key Features:
------------
1. Simulated TrueRNG devices with configurable behavior
2. Thread-safe concurrent reading from multiple devices
3. Deterministic pattern generation for testing
4. True random data generation using os.urandom
5. Configurable data rates and buffer sizes

Usage:
------
1. Basic usage with random data:
   ```python
   reader = create_mock_reader(num_devices=8, pattern_mode=False)
   data = reader.get_data()  # Returns list of bytes objects
   reader.stop_reading()
   ```

2. Pattern mode for testing:
   ```python
   reader = create_mock_reader(num_devices=4, pattern_mode=True)
   data = reader.get_data()  # Returns predictable patterns
   reader.stop_reading()
   ```

Components:
----------
- MockRNGDevice: Individual mock device implementation
- MockRNGReader: Manager for multiple mock devices
- create_mock_reader: Factory function for easy setup

Thread Safety:
------------
All operations are thread-safe and support concurrent access from multiple
threads. The implementation uses Queue for thread-safe data transfer and
Event for clean shutdown.
"""

import os
import random
import logging
from typing import List, Optional
from dataclasses import dataclass
from queue import Queue
from threading import Thread, Event

logger = logging.getLogger(__name__)

@dataclass
class MockRNGDevice:
    """
    Simulates a single TrueRNG device with configurable data generation.
    
    This class provides a mock implementation of a TrueRNG device that can either:
    1. Generate true random data using os.urandom (default mode)
    2. Generate deterministic patterns for testing (pattern mode)
    
    In pattern mode, each device generates a unique repeating pattern based on
    its device_id, making it easy to verify data integrity in the pipeline.
    
    Attributes:
        device_id: Unique identifier for this device (0-based)
        pattern_mode: Whether to generate deterministic patterns
        pattern_length: Length of repeating pattern in pattern mode
    
    Example:
        # Create a mock device in random mode
        device = MockRNGDevice(device_id=0)
        data = device.read(250)  # Get 250 random bytes
        
        # Create a mock device in pattern mode
        device = MockRNGDevice(device_id=1, pattern_mode=True)
        data = device.read(100)  # Get 100 bytes of repeating pattern
    """
    device_id: int
    pattern_mode: bool = False
    pattern_length: int = 1000
    
    def __post_init__(self):
        """
        Initialize the device after creation.
        
        In pattern mode, generates a unique repeating pattern based on device_id.
        The pattern is a sequence of bytes where each byte is (index + device_id) % 256.
        """
        if self.pattern_mode:
            # Create a unique repeating pattern for this device
            self.pattern = bytes([(i + self.device_id) % 256 
                                for i in range(self.pattern_length)])
            self.pattern_index = 0
            logger.debug(f"Initialized device {self.device_id} in pattern mode "
                        f"with {self.pattern_length} byte pattern")
    
    def read(self, num_bytes: int) -> bytes:
        """
        Read specified number of bytes from the mock device.
        
        In pattern mode, returns bytes from the pre-generated repeating pattern.
        In random mode, returns true random bytes from os.urandom.
        
        Args:
            num_bytes: Number of bytes to read
            
        Returns:
            bytes: Generated data of requested length
        """
        if self.pattern_mode:
            # Return bytes from repeating pattern
            result = bytearray()
            for _ in range(num_bytes):
                result.append(self.pattern[self.pattern_index])
                self.pattern_index = (self.pattern_index + 1) % self.pattern_length
            return bytes(result)
        else:
            # Return true random bytes
            return os.urandom(num_bytes)

class MockRNGReader:
    """
    Manages multiple mock RNG devices and provides concurrent reading capability.
    
    This class simulates the behavior of multiple TrueRNG devices operating
    concurrently. It manages background threads for each device and provides
    thread-safe access to the generated data.
    
    Features:
    - Concurrent reading from multiple devices
    - Thread-safe data access via queues
    - Clean shutdown handling
    - Configurable data generation mode
    
    Example:
        reader = MockRNGReader(num_devices=8)
        reader.start_reading(bytes_per_second=250)
        data = reader.get_data()  # Returns list of bytes from all devices
        reader.stop_reading()
    """
    def __init__(self, num_devices: int = 8, pattern_mode: bool = False):
        """
        Initialize the mock RNG reader.
        
        Args:
            num_devices: Number of mock devices to create
            pattern_mode: Whether devices should generate patterns
        """
        self.devices = [MockRNGDevice(i, pattern_mode) for i in range(num_devices)]
        self.queues = [Queue() for _ in range(num_devices)]
        self.stop_event = Event()
        self.threads: List[Optional[Thread]] = [None] * num_devices
        logger.info(f"Initialized {num_devices} mock RNG devices in "
                   f"{'pattern' if pattern_mode else 'random'} mode")
    
    def start_reading(self, bytes_per_second: int = 250):
        """
        Start concurrent reading from all mock devices.
        
        Creates and starts a background thread for each device that continuously
        generates data at the specified rate.
        
        Args:
            bytes_per_second: Number of bytes to generate per second per device
        """
        for i, device in enumerate(self.devices):
            if self.threads[i] is None or not self.threads[i].is_alive():
                self.threads[i] = Thread(
                    target=self._read_loop,
                    args=(device, self.queues[i], bytes_per_second),
                    daemon=True
                )
                self.threads[i].start()
                logger.debug(f"Started reading thread for mock device {i}")
    
    def stop_reading(self):
        """
        Stop all reading threads and clean up resources.
        
        Sets the stop event and waits for all threads to finish.
        Threads will complete their current read cycle before stopping.
        """
        self.stop_event.set()
        for thread in self.threads:
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
        self.stop_event.clear()
        logger.debug("Stopped all mock RNG reading threads")
    
    def _read_loop(self, device: MockRNGDevice, queue: Queue, bytes_per_second: int):
        """
        Background thread function for continuous device reading.
        
        Reads data from the device at regular intervals and puts it in the queue.
        Continues until stop_event is set.
        
        Args:
            device: MockRNGDevice to read from
            queue: Queue to store the read data
            bytes_per_second: Data generation rate
        """
        while not self.stop_event.is_set():
            try:
                data = device.read(bytes_per_second)
                queue.put(data)
                # Simulate real device timing
                self.stop_event.wait(1.0)
            except Exception as e:
                logger.error(f"Error reading from mock device {device.device_id}: {e}")
                break
    
    def get_data(self) -> List[bytes]:
        """
        Get the latest data from all devices.
        
        Returns:
            List[bytes]: List of data chunks from each device.
                        Empty bytes object if no data available.
        """
        result = []
        for q in self.queues:
            try:
                data = q.get_nowait()
                result.append(data)
            except:
                # Return empty bytes if no data available
                result.append(bytes())
        return result

def create_mock_reader(num_devices: int = 8, pattern_mode: bool = False) -> MockRNGReader:
    """
    Factory function to create and initialize a mock RNG reader.
    
    This is the recommended way to create a MockRNGReader instance as it
    handles initialization and starts the reading threads automatically.
    
    Args:
        num_devices: Number of mock devices to create
        pattern_mode: Whether to use deterministic patterns
    
    Returns:
        MockRNGReader: Initialized and running mock RNG reader
    
    Example:
        reader = create_mock_reader(num_devices=4, pattern_mode=True)
        try:
            data = reader.get_data()
            # Process data...
        finally:
            reader.stop_reading()
    """
    reader = MockRNGReader(num_devices, pattern_mode)
    reader.start_reading()
    return reader 