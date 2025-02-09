
import os
import json
import sys

def main():
    try:
        os.chdir("/Users/raymonddeoliveira/stable-diffusion")
        cmd = "python scripts/txt2img.py --prompt 'arnor transmutation greats ' --plms --H 512 --W 512 --n_samples 1 --ckpt sd-v1-4.ckpt"
        result = os.system(cmd)
        
        with open("sd_status.json", 'w') as f:
            if result == 0:
                latest_file = sorted(os.listdir('outputs/txt2img-samples'))[-2]
                json.dump({'success': True, 'file': latest_file}, f)
            else:
                json.dump({'success': False, 'error': f'Command failed with exit code {result}'}, f)
    except Exception as e:
        with open("sd_status.json", 'w') as f:
            json.dump({'success': False, 'error': str(e)}, f)

if __name__ == '__main__':
    main()
