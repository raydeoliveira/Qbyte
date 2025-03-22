## Qbyte.py
Data Visualization for Hybrid-Quantum Clock featuring Q-Byte Processing

This is an R&D project with the endgoal of integrating biofrequencies into visual language.

By activating this on your desktop you will have a functioning clock featuring UTC time with Q-Byte Processing and with our data visualization features you get to experience the spatial qualites of time. This clock unifies the laws of quantum tunneling mechanics and relativity. For further detailed explantion you can download our white paper here: https://26b2ca43-c1dd-4e13-ad9f-98838f540014.filesusr.com/ugd/eb9cf8_22349fce691a4c1ead2d85d4c95c344b.pdf

Our blockchain version of QByte Processing can be found here: http://haloai.co

Review Dr. Samantha Caputi's explanation video here: https://www.youtube.com/watch?v=3XkcAKzz61Q&t=2s

## Getting Started

### System Requirements
- Python 3.6 or higher
- Required Python packages (see requirements.txt)
- TrueRNG hardware (optional) - will use pseudo-random number generation if hardware isn't detected

### Installation 

1. Clone this repository onto your local machine
   ```
   git clone https://github.com/your-username/Qbyte.git
   cd Qbyte
   ```

2. Install required dependencies
   ```
   pip install -r requirements.txt
   ```

3. Configure your desired settings at the top of 'QByte.py'. The comments explain what each setting is.

### Running QByte

Run 'QByte.py' from the command line as follows:

```
python QByte.py [mode] [remarks]
```

Parameters:
- **MODE**: This can be 'static' or 'auto'. The only difference between the two is that the 'auto' mode will automatically switch views every 10 minutes.
- **REMARKS**: This is an easy way to remember your session. You can input anything without spaces.
  
Examples:

```
python QByte.py static BirthdayParty
python QByte.py auto FamilyGathering
```

### macOS Specific Instructions

QByte is fully compatible with macOS systems. Some tips for macOS users:

1. **TrueRNG Device Detection**: The program will automatically detect TrueRNG devices connected to your Mac. If no devices are found, it will use the pseudorandom number generator instead.

2. **Python Environment**: We recommend using a conda environment or venv for a clean installation.
   ```
   conda create -n qbyte python=3.8
   conda activate qbyte
   pip install -r requirements.txt
   ```

3. **Display Issues**: If you encounter display problems, ensure you're using TkAgg as the matplotlib backend (this is set by default in the code).

4. **Device Permissions**: On newer macOS versions, you may need to grant permissions for the application to access USB devices. Check System Preferences → Security & Privacy if prompted.

### Troubleshooting

If you encounter issues:

1. Check the console output for informational messages and warnings.
2. Review the log file (qbyte_rng.log) for more detailed error information.
3. Ensure all required Python packages are installed.
4. If using TrueRNG hardware, verify the devices are properly connected and recognized by your system.
5. Try running in PRNG mode by setting `RandomSrc = 'prng'` in the configuration section.

## Output Files

As you run a session, data files are produced in the `dataout` directory:

- `QB_<timestamp>_<session>_<remarks>.txt`: Contains the raw data from your session
- `QB_<timestamp>_<remarks>_C.txt`: Contains any comments you entered during the session
- `QB_<timestamp>_<remarks>_SD.txt`: Contains Stable Diffusion image generation data (if enabled)

### Stable Diffusion Integration

Q-Byte Processing can be run with Stable Diffusion, a new AI image generating module. This will create images of the words that appear when the colors change. Stable diffusion can be ontained from the github repo: https://github.com/CompVis/stable-diffusion

The model checkpoints can be obtained using a Curl command:

```
curl https://www.googleapis.com/storage/v1/b/aai-blog-files/o/sd-v1-4.ckpt?alt=media > sd-v1-4.ckpt
```

You will need to provide a path to your local stable diffusion directory in the QByte.py configuration.

We've created a conda enviornment, qbenv.yaml, which works with both QByte and Stable Diffusion. To create this enviornment:

```
conda env create -f qbenv.yaml
```

Then activate it:

```
conda activate ldmqb
```

Then run the python QByte.py command as described above.

## QBread.py

To re-analyze the raw data from a prior session, run 'QBread.py' as follows:

```
python QBread.py input_file
```
  
Example:

```
python QBread.py QB_1630886880_BirthdayParty.txt
```

## MakeWordclouds.py

This script will create words from a given run. Input a filename and username. Example:

```
python MakeWordclouds.py Samantha QB_xxx.txt
```
