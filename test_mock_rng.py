"""
Test suite for mock RNG implementation and data pipeline integrity.

This module tests:
1. Pattern generation and consistency across mock devices
2. Concurrent reading without data loss or corruption
3. Data aggregation accuracy
4. Thread safety and cleanup
"""

import unittest
import time
from typing import List, Dict
import threading
from queue import Queue
import logging

from mock_rng import MockRNGDevice, MockRNGReader, create_mock_reader
from rng_manager import RNGManager
from config import RNGConfig

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestMockRNG(unittest.TestCase):
    """Test cases for mock RNG implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Configure for testing
        RNGConfig.SOURCE = 'mock'
        RNGConfig.MOCK_PATTERN_MODE = True
        RNGConfig.MOCK_PATTERN_LENGTH = 1000
        RNGConfig.SPEED = 250  # bytes per second
        RNGConfig.NUM_DEVICES = 4  # Use fewer devices for testing
        
        self.rng_manager = RNGManager()
        
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'rng_manager'):
            self.rng_manager.cleanup()
    
    def test_pattern_generation(self):
        """Test that each device generates its expected pattern"""
        device = MockRNGDevice(device_id=0, pattern_mode=True, pattern_length=1000)
        data = device.read(1000)
        
        # Verify pattern matches expected sequence
        expected = bytes([i % 256 for i in range(1000)])
        self.assertEqual(data, expected, "Pattern generation mismatch")
        
        # Verify pattern repeats correctly
        next_chunk = device.read(500)
        expected_repeat = bytes([i % 256 for i in range(500)])
        self.assertEqual(next_chunk, expected_repeat, "Pattern does not repeat correctly")
    
    def test_concurrent_reading(self):
        """Test concurrent reading from multiple devices without data loss"""
        # Initialize devices
        self.assertTrue(self.rng_manager.initialize_devices())
        
        # Read data for a few seconds
        NUM_READS = 5
        all_data: List[List[bytes]] = []
        
        for _ in range(NUM_READS):
            data, _ = self.rng_manager.read_data()
            all_data.append(data)
            time.sleep(1.0)  # Wait for next read cycle
            
        # Verify data integrity for each device
        for device_idx in range(RNGConfig.NUM_DEVICES):
            expected_pattern = bytes([(i + device_idx) % 256 
                                    for i in range(RNGConfig.SPEED)])
            
            for read_idx in range(NUM_READS):
                actual = all_data[read_idx][device_idx]
                expected = bytes([(i + device_idx + (read_idx * RNGConfig.SPEED)) % 256 
                                for i in range(RNGConfig.SPEED)])
                
                self.assertEqual(
                    actual, 
                    expected,
                    f"Data mismatch for device {device_idx} at read {read_idx}"
                )
    
    def test_pattern_uniqueness(self):
        """Test that each device generates a unique pattern"""
        patterns: Dict[bytes, int] = {}
        
        for device_id in range(RNGConfig.NUM_DEVICES):
            device = MockRNGDevice(device_id, pattern_mode=True)
            pattern = device.read(100)  # Read a sample to check uniqueness
            
            self.assertNotIn(
                pattern, 
                patterns, 
                f"Device {device_id} generated duplicate pattern"
            )
            patterns[pattern] = device_id
    
    def test_thread_safety(self):
        """Test thread safety of the mock RNG reader"""
        reader = create_mock_reader(
            num_devices=RNGConfig.NUM_DEVICES,
            pattern_mode=True
        )
        
        # Create multiple threads that read simultaneously
        NUM_THREADS = 10
        results = Queue()
        
        def read_data():
            try:
                data = reader.get_data()
                results.put(("success", data))
            except Exception as e:
                results.put(("error", str(e)))
        
        threads = [
            threading.Thread(target=read_data)
            for _ in range(NUM_THREADS)
        ]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=2.0)
        
        # Check results
        errors = []
        while not results.empty():
            status, data = results.get()
            if status == "error":
                errors.append(data)
        
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        
        # Cleanup
        reader.stop_reading()
    
    def test_cleanup(self):
        """Test proper cleanup of resources"""
        reader = create_mock_reader(
            num_devices=RNGConfig.NUM_DEVICES,
            pattern_mode=True
        )
        
        # Verify threads are running
        for thread in reader.threads:
            self.assertTrue(thread.is_alive())
        
        # Stop reading and verify cleanup
        reader.stop_reading()
        time.sleep(0.1)  # Give threads time to stop
        
        for thread in reader.threads:
            self.assertFalse(thread.is_alive())

if __name__ == '__main__':
    unittest.main() 