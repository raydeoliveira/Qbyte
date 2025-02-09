#!/usr/bin/env python3
"""
Parameter Sweep Analysis for QByte Coherence Thresholds
====================================================

This script performs a comprehensive analysis of how different Z-score thresholds 
affect coherence event detection in the QByte system. It helps identify optimal 
threshold values that achieve desired event rates.

Key Features:
------------
1. Automated sweep through configurable ranges of Z-score thresholds
2. Separate analysis for color and rotation coherence events
3. Mock RNG data generation for reproducible testing
4. CSV output of all results for further analysis
5. Visualization of threshold vs event rate relationships
6. Summary statistics including optimal threshold identification

Usage:
------
1. Run directly: ./parameter_sweep.py
2. Import and use functions: 
   from parameter_sweep import run_single_config, plot_results

Configuration:
-------------
- Adjust SweepConfig parameters to modify test ranges and duration
- Update ProcessingConfig values to change baseline thresholds
- Modify RNGConfig settings to adjust data generation parameters

Output:
-------
1. CSV file with detailed results (zscore_sweep_TIMESTAMP.csv)
2. PNG plot of threshold vs event relationships (zscore_sweep_TIMESTAMP.png)
3. Printed summary statistics including optimal thresholds
"""

import os
import csv
import time
import logging
from typing import List, Tuple, Dict
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

from config import (
    RNGConfig,
    ProcessingConfig,
    PathConfig,
    runtime_config,
    update_runtime_config
)
from mock_rng import create_mock_reader
from rng_manager import RNGManager

# Configure logging with timestamp and level for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SweepConfig:
    """
    Configuration parameters for the parameter sweep analysis.
    
    Attributes:
        color_z_range: Tuple of (start, stop, step) for color Z-score sweep
        rot_z_range: Tuple of (start, stop, step) for rotation Z-score sweep
        sample_time: Duration in seconds to test each configuration
        bytes_per_read: Number of bytes to read in each RNG cycle
    
    Example:
        config = SweepConfig(
            color_z_range=(1.0, 3.0, 0.1),  # Test from 1.0 to 3.0 in steps of 0.1
            sample_time=300  # Run each test for 5 minutes
        )
    """
    color_z_range: Tuple[float, float, float] = (1.0, 3.0, 0.1)
    rot_z_range: Tuple[float, float, float] = (1.0, 3.0, 0.1)
    sample_time: int = 300
    bytes_per_read: int = 250

@dataclass
class SweepResult:
    """
    Container for results from a single parameter configuration test.
    
    Attributes:
        color_z: Color coherence Z-score threshold used
        rot_z: Rotation coherence Z-score threshold used
        color_events: Number of color coherence events detected
        rot_events: Number of rotation coherence events detected
        total_reads: Total number of RNG read cycles performed
        runtime: Actual duration of the test in seconds
        color_event_rate: Color events per second
        rot_event_rate: Rotation events per second
    """
    color_z: float
    rot_z: float
    color_events: int
    rot_events: int
    total_reads: int
    runtime: float
    color_event_rate: float
    rot_event_rate: float

def setup_mock_data() -> RNGManager:
    """
    Initialize the mock RNG system for testing.
    
    This function configures the RNG system to use mock devices that generate
    predictable patterns, allowing for reproducible testing of the coherence
    detection algorithms.
    
    Returns:
        RNGManager: Initialized RNG manager with mock devices
    
    Raises:
        RuntimeError: If mock RNG devices cannot be initialized
    """
    # Configure mock RNG settings
    RNGConfig.SOURCE = 'mock'
    RNGConfig.MOCK_PATTERN_MODE = True
    RNGConfig.SPEED = 250  # Bytes per second per device
    RNGConfig.NUM_DEVICES = 8  # Number of mock devices to simulate
    
    # Initialize and verify RNG manager
    rng_manager = RNGManager()
    if not rng_manager.initialize_devices():
        raise RuntimeError("Failed to initialize mock RNG devices")
    return rng_manager

def check_coherence(data: bytes, expected_bits: int, z_threshold: float) -> bool:
    """
    Check if the data exceeds the coherence threshold.
    
    This function implements the core coherence detection algorithm:
    1. Counts the number of '1' bits in the input data
    2. Calculates the deviation from the expected number of bits
    3. Compares the normalized deviation to the Z-score threshold
    
    Args:
        data: Raw bytes to analyze
        expected_bits: Expected number of '1' bits (typically len(data) * 8 / 2)
        z_threshold: Z-score threshold for coherence detection
    
    Returns:
        bool: True if coherence threshold is exceeded, False otherwise
    """
    # Count actual number of '1' bits in the data
    bit_count = sum(1 for byte in data for bit in bin(byte)[2:].zfill(8) if bit == '1')
    
    # Calculate deviation and standard deviation
    deviation = abs(bit_count - expected_bits)
    std_dev = (expected_bits * 0.25) ** 0.5  # Theoretical std dev for binary data
    
    # Compare normalized deviation to threshold
    return (deviation / std_dev) > z_threshold

def run_single_config(
    rng_manager: RNGManager,
    color_z: float,
    rot_z: float,
    sample_time: int,
    bytes_per_read: int
) -> SweepResult:
    """Run test with specific Z-score thresholds"""
    start_time = time.time()
    end_time = start_time + sample_time
    
    color_events = 0
    rot_events = 0
    total_reads = 0
    expected_bits = bytes_per_read * 4  # Expected number of 1s in random data
    
    while time.time() < end_time:
        data, _ = rng_manager.read_data()
        total_reads += 1
        
        # Combine data from all devices
        combined = b''.join(d for d in data if d)
        
        # Check for events
        if check_coherence(combined, expected_bits, color_z):
            color_events += 1
        if check_coherence(combined, expected_bits, rot_z):
            rot_events += 1
            
        time.sleep(0.1)  # Prevent overwhelming the system
    
    runtime = time.time() - start_time
    
    return SweepResult(
        color_z=color_z,
        rot_z=rot_z,
        color_events=color_events,
        rot_events=rot_events,
        total_reads=total_reads,
        runtime=runtime,
        color_event_rate=color_events / runtime,
        rot_event_rate=rot_events / runtime
    )

def save_results(results: List[SweepResult], output_dir: str):
    """Save results to CSV file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f'zscore_sweep_{timestamp}.csv')
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Color Z-Score',
            'Rotation Z-Score',
            'Color Events',
            'Rotation Events',
            'Total Reads',
            'Runtime (s)',
            'Color Event Rate (Hz)',
            'Rotation Event Rate (Hz)'
        ])
        
        for result in results:
            writer.writerow([
                result.color_z,
                result.rot_z,
                result.color_events,
                result.rot_events,
                result.total_reads,
                result.runtime,
                result.color_event_rate,
                result.rot_event_rate
            ])
    
    logger.info(f"Results saved to {output_file}")

def print_summary(results: List[SweepResult]):
    """
    Print a human-readable summary of the parameter sweep results.
    
    This function analyzes the results and prints:
    1. Statistical summary of color event rates
    2. Statistical summary of rotation event rates
    3. Optimal thresholds for achieving target event rate (0.1 Hz)
    
    Args:
        results: List of SweepResult objects from the parameter sweep
    """
    print("\nParameter Sweep Summary")
    print("=" * 50)
    
    # Analyze color events
    color_rates = [r.color_event_rate for r in results]
    print(f"\nColor Event Rates (Hz):")
    print(f"  Min: {min(color_rates):.3f}")
    print(f"  Max: {max(color_rates):.3f}")
    print(f"  Mean: {np.mean(color_rates):.3f}")
    print(f"  Median: {np.median(color_rates):.3f}")
    
    # Find optimal thresholds (closest to target rate of 0.1 Hz)
    optimal_color = min(results, key=lambda r: abs(r.color_event_rate - 0.1))
    optimal_rot = min(results, key=lambda r: abs(r.rot_event_rate - 0.1))
    
    print(f"\nOptimal Thresholds (targeting 0.1 Hz event rate):")
    print(f"  Color Z-Score: {optimal_color.color_z:.2f}")
    print(f"  Rotation Z-Score: {optimal_rot.rot_z:.2f}")

def plot_results(results: List[SweepResult], output_dir: str):
    """
    Create and save visualizations of the parameter sweep results.
    
    Generates a two-panel figure showing:
    1. Color coherence event rate vs Z-score threshold
    2. Rotation coherence event rate vs Z-score threshold
    
    Each panel includes:
    - Event rate curve with shaded area
    - Target rate line (0.1 Hz)
    - Grid lines and labels
    - Legend
    
    Args:
        results: List of SweepResult objects to visualize
        output_dir: Directory to save the plot PNG file
    """
    # Set up the plot style for better visualization
    plt.style.use('seaborn')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
    fig.suptitle('Z-Score Threshold vs Coherence Events', fontsize=14)
    
    # Separate results for color and rotation analysis
    color_results = [r for r in results if r.rot_z == ProcessingConfig.ROT_Z]
    rot_results = [r for r in results if r.color_z != ProcessingConfig.ROT_Z]
    
    # Plot color coherence results
    color_z = [r.color_z for r in color_results]
    color_rates = [r.color_event_rate for r in color_results]
    ax1.plot(color_z, color_rates, 'b-', linewidth=2, label='Event Rate')
    ax1.fill_between(color_z, color_rates, alpha=0.2)
    ax1.set_title('Color Coherence Events')
    ax1.set_xlabel('Color Z-Score Threshold')
    ax1.set_ylabel('Events per Second')
    ax1.grid(True)
    
    # Add target rate reference line
    ax1.axhline(y=0.1, color='r', linestyle='--', label='Target Rate (0.1 Hz)')
    ax1.legend()
    
    # Plot rotation coherence results
    rot_z = [r.rot_z for r in rot_results]
    rot_rates = [r.rot_event_rate for r in rot_results]
    ax2.plot(rot_z, rot_rates, 'g-', linewidth=2, label='Event Rate')
    ax2.fill_between(rot_z, rot_rates, alpha=0.2)
    ax2.set_title('Rotation Coherence Events')
    ax2.set_xlabel('Rotation Z-Score Threshold')
    ax2.set_ylabel('Events per Second')
    ax2.grid(True)
    
    # Add target rate reference line
    ax2.axhline(y=0.1, color='r', linestyle='--', label='Target Rate (0.1 Hz)')
    ax2.legend()
    
    # Adjust layout and save high-resolution plot
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_file = os.path.join(output_dir, f'zscore_sweep_{timestamp}.png')
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"Plot saved to {plot_file}")
    
    # Display plot interactively
    plt.show()

def main():
    """
    Main execution function for the parameter sweep analysis.
    
    This function:
    1. Sets up the test environment and mock RNG devices
    2. Performs the parameter sweep for color Z-scores
    3. Finds optimal color Z-score
    4. Performs the parameter sweep for rotation Z-scores
    5. Saves results and generates visualizations
    6. Ensures proper cleanup of resources
    
    The analysis is performed in two phases:
    1. Color sweep: Tests different color Z-scores with fixed rotation Z-score
    2. Rotation sweep: Tests different rotation Z-scores with optimal color Z-score
    """
    sweep_config = SweepConfig()
    results: List[SweepResult] = []
    
    # Ensure output directory exists
    os.makedirs(PathConfig.DATA_DIR, exist_ok=True)
    
    try:
        # Initialize mock RNG system
        rng_manager = setup_mock_data()
        
        # Phase 1: Sweep color Z-scores
        base_rot_z = ProcessingConfig.ROT_Z
        color_range = np.arange(*sweep_config.color_z_range)
        
        for color_z in color_range:
            logger.info(f"Testing Color Z-Score: {color_z:.2f}")
            result = run_single_config(
                rng_manager,
                color_z,
                base_rot_z,
                sweep_config.sample_time,
                sweep_config.bytes_per_read
            )
            results.append(result)
        
        # Phase 2: Sweep rotation Z-scores with optimal color Z-score
        optimal_color_z = min(results, key=lambda r: abs(r.color_event_rate - 0.1)).color_z
        rot_range = np.arange(*sweep_config.rot_z_range)
        
        for rot_z in rot_range:
            logger.info(f"Testing Rotation Z-Score: {rot_z:.2f}")
            result = run_single_config(
                rng_manager,
                optimal_color_z,
                rot_z,
                sweep_config.sample_time,
                sweep_config.bytes_per_read
            )
            results.append(result)
        
        # Generate output
        save_results(results, PathConfig.DATA_DIR)
        print_summary(results)
        plot_results(results, PathConfig.DATA_DIR)
        
    finally:
        # Ensure proper cleanup of RNG resources
        if 'rng_manager' in locals():
            rng_manager.cleanup()

if __name__ == '__main__':
    main() 