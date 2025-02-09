# QByte: Quantum Random Number Generator Analysis Suite

A comprehensive toolkit for analyzing quantum random number generation using TrueRNG devices, with support for coherence detection, statistical analysis, and visualization.

## Features

- Real-time quantum random number data acquisition from TrueRNG devices
- Mock RNG support for testing and development
- Advanced coherence detection algorithms
- Statistical analysis including Cohen's d effect size calculation
- Parameter optimization through automated sweeps
- Real-time visualization of quantum data patterns
- Comprehensive data logging and event tracking
- Support for both single-session and long-term monitoring

## Installation

### Prerequisites

- Python 3.8 or higher
- macOS, Linux, or Windows with appropriate USB drivers
- TrueRNG device(s) for hardware-based testing

### Dependencies Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Qbyte.git
   cd Qbyte
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

Key dependencies include:
- numpy
- matplotlib
- pyserial
- scipy
- astral
- tkinter (usually comes with Python)

## Usage Scenarios

### 1. Basic RNG Data Collection

#### With Physical TrueRNG Device:
```bash
python QByte.py static
```

#### With Mock RNG (for testing):
```bash
python QByte.py static --source mock
```

### 2. Parameter Sweep Analysis

Run a comprehensive sweep of Z-score thresholds to optimize coherence detection:

```bash
python parameter_sweep.py
```

Key features:
- Automatically tests range of color and rotation Z-scores
- Generates visualization of threshold vs event relationships
- Saves detailed results to CSV
- Produces summary statistics and optimal threshold recommendations

### 3. Coherence Monitoring Session

#### Quick Pilot Session (10 minutes):
```bash
python run_coherence_session.py --duration 600 --source trng
```

#### Testing with Mock Data:
```bash
python run_coherence_session.py --duration 300 --source mock
```

Options:
- `--duration`: Session length in seconds
- `--source`: 'trng' for TrueRNG device, 'mock' for testing
- `--color-z`: Color coherence Z-score threshold
- `--rot-z`: Rotation coherence Z-score threshold
- `--outdir`: Custom output directory

### 4. Automated Long-term Monitoring

```bash
python QByte.py auto
```

## Data Output

The system generates several types of output files:

1. Raw Data Files:
   - `QB_TIMESTAMP_REMARKS.txt`: Raw byte streams and events
   - `raw_data_TIMESTAMP.csv`: Detailed device readings

2. Analysis Results:
   - `zscore_sweep_TIMESTAMP.csv`: Parameter sweep results
   - `zscore_sweep_TIMESTAMP.png`: Visualization plots
   - `statistics_TIMESTAMP.txt`: Statistical analysis including Cohen's d

3. Event Logs:
   - `events_TIMESTAMP.log`: Detected coherence events
   - `QB_TIMESTAMP_REMARKS_C.txt`: User comments and annotations

## Configuration

Key configuration files:

1. `config.py`: Central configuration system
   - RNG device settings
   - Processing parameters
   - Visualization options
   - Output paths

2. `pytest.ini`: Test configuration
   - Logging settings
   - Test discovery rules

## Statistical Analysis

The system now includes advanced statistical analysis:

- Baseline vs. Focus Period Comparison
  - First 2 minutes used as baseline
  - Remaining time as focus period
  - Cohen's d effect size calculation
  - Automatic interpretation of effect sizes

## Troubleshooting

Common issues and solutions:

1. TrueRNG Device Not Detected:
   - Check USB connection
   - Verify device permissions
   - Ensure proper drivers are installed

2. Visualization Issues:
   - Confirm matplotlib backend configuration
   - Check for tkinter installation
   - Verify display server connection

3. Performance Concerns:
   - Adjust buffer sizes in config.py
   - Monitor system resource usage
   - Consider using mock devices for testing

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description

## License

[Your License Information Here]

## Contact

[Your Contact Information Here]

## Qbyte.py
Data Visualization for Hybrid-Quantum Clock featuring Q-Byte Processing

This is an R&D project with the endgoal of integrating biofrequencies into visual language.

By activating this on your desktop you will have a functioning clock featuring UTC time with Q-Byte Processing and with our data visualization features you get to experience the spatial qualites of time. This clock unifies the laws of quantum tunneling mechanics and relativity. For further detailed explantion you can download our white paper here: https://26b2ca43-c1dd-4e13-ad9f-98838f540014.filesusr.com/ugd/eb9cf8_22349fce691a4c1ead2d85d4c95c344b.pdf

Our blockchain version of QByte Processing can be found here: http://haloai.co

Review Dr. Samantha Caputi's explanation video here: https://www.youtube.com/watch?v=3XkcAKzz61Q&t=2s

Steps to run locally:

1. Clone this directory onto your local machine
2. Run 'pip install -r requirements.txt'
3. Configure your desired settings at the top of 'QByte.py'. The comments explain what each setting is.
4. Run 'QByte.py' from the command line as follows:

$ python QByte.py mode remarks

MODE: This can be 'static' or 'auto'. The only difference between the two is that the 'auto' mode will automatically switch views every 10 minutes.

REMARKS: This is an easy way to remember your session. You can input anything without spaces.
  
Examples:

python QByte.py static BirthdayParty

python QByte.py auto FamilyGathering
  
As you run a session, two files are produced that are timestamped with the initialization. The one labeled '*_C.txt' contains any comments you entered, and the other contains the raw data.

### Stable Diffusion

Q-Byte Processing can be run with Stable Diffusion, a new AI image generating module. This will create images of the words that appear when the colors change. Stable diffusion can be ontained from the github repo: https://github.com/CompVis/stable-diffusion

The model checkpoints can be obtained using a Curl command:

$ curl https://www.googleapis.com/storage/v1/b/aai-blog-files/o/sd-v1-4.ckpt?alt=media > sd-v1-4.ckpt

You will need to provide a path to your local stable diffusion directory in the QByte.py configuration.

We've created a conda enviornment, qbenv.yaml, which works with both QByte and Stable Diffusion. To create this enviornment:

$ conda env create -f qbenv.yaml

Then activate it:

$ conda activate ldmqb

Then run the python QByte.py command as described above.

## QBread.py

To re-analyze the raw data from a prior session, run 'QBread.py' as follows:

python QBread.py input_file
  
Example:

$ python QBread.py QB_1630886880_BirthdayParty.txt

## MakeWordclouds.py

This script will create words from a given run. Input a filename and username. Example:

$ python MakeWordclouds.py Samantha QB_xxx.txt
