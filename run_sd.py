
import os
import sys
import json
from subprocess import check_output, CalledProcessError

STABLE_DIFFUSION_DIR = "/Users/raymonddeoliveira/stable-diffusion"
os.chdir(STABLE_DIFFUSION_DIR)

try:
    # Using smaller image size (256x256) and fewer steps (10) for faster generation
    cmd = f'python scripts/txt2img.py --prompt "neural interface" --plms --n_samples 1 --n_iter 1 --ddim_steps 10 --H 256 --W 256'
    output = check_output(cmd, shell=True, text=True)
    result = {"success": True, "output": output}
except CalledProcessError as e:
    result = {"success": False, "error": str(e)}
except Exception as e:
    result = {"success": False, "error": str(e)}

with open("sd_status.json", "w") as f:
    json.dump(result, f)
