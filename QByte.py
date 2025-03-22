import matplotlib
matplotlib.use('TkAgg')  # Set the backend before other matplotlib imports

from mpl_toolkits.mplot3d import Axes3D  # required import for some machines to render 3d projection
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
import os
import subprocess
import json
import sys
import serial
from serial.tools import list_ports
import time
import math
import scipy.stats
import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg
import warnings
from matplotlib.widgets import Button
import tkinter as tk
from astral import LocationInfo
import datetime
from astral.sun import sunrise,sunset
from urllib.request import urlopen as uReq
import logging
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional
import platform

@dataclass
class RNGData:
    """Container for RNG device data"""
    device_id: str
    data: bytes
    timestamp: float
    
class RNGReader:
    """Concurrent reader for multiple RNG devices"""
    def __init__(self, num_devices: int, buffer_size: int = 1000):
        self.data_queue = queue.Queue(maxsize=buffer_size)
        self.stop_event = threading.Event()
        self.devices = []
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=num_devices)
        self._initialized = False
        
    def read_device(self, device_id: str, ser: serial.Serial, ned_speed: int):
        """Reader thread for a single device"""
        logger.debug(f"Reader thread started", extra={'device_id': device_id})
        while not self.stop_event.is_set():
            try:
                with self.lock:  # Protect serial port access
                    ser.flushInput()
                    data = ser.read(ned_speed)
                    
                if len(data) == ned_speed:
                    logger.debug(f"Read complete - received {len(data)} bytes", 
                               extra={'device_id': device_id})
                    rng_data = RNGData(
                        device_id=device_id,
                        data=data,
                        timestamp=time.time()
                    )
                    self.data_queue.put(rng_data, timeout=1.0)
                else:
                    logger.warning(f"Incomplete read: {len(data)} bytes", 
                                 extra={'device_id': device_id})
                    
            except Exception as e:
                logger.error(f"Device read failed: {str(e)}", 
                           extra={'device_id': device_id})
                time.sleep(1)  # Back off on error
                
    def start_readers(self, ser_ports: List[serial.Serial], ned_speed: int):
        """Start reader threads for all devices"""
        if self._initialized:
            return
            
        for idx, ser_port in enumerate(ser_ports):
            device_id = f"RNG{idx}"
            future = self.executor.submit(self.read_device, device_id, ser_port, ned_speed)
            self.devices.append((device_id, future))
            
        self._initialized = True
            
    def get_data(self, timeout: float = 0.1) -> List[RNGData]:
        """Get accumulated data from all devices"""
        data = []
        start_time = time.time()
        max_wait = 2.0  # Maximum time to wait for all devices
        
        while len(data) < len(self.devices):
            try:
                item = self.data_queue.get(timeout=timeout)
                data.append(item)
            except queue.Empty:
                if time.time() - start_time > max_wait:
                    logger.warning(f"Timeout waiting for device data. Got {len(data)}/{len(self.devices)} devices")
                    break
        
        # Sort by device ID for consistent ordering
        data.sort(key=lambda x: int(x.device_id[3:]))
        return data
        
    def stop(self):
        """Stop all reader threads"""
        self.stop_event.set()
        self.executor.shutdown(wait=True)
        self._initialized = False

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Device %(device_id)s] - %(message)s')

# Add file handler
fh = logging.FileHandler('qbyte_rng.log')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Configure console handler for important messages
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch_formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(ch_formatter)
logger.addHandler(ch)

# Add a filter to provide default values for missing attributes
class DefaultFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'device_id'):
            record.device_id = 'main'
        return True

logger.addFilter(DefaultFilter())

os.environ['TK_SILENCE_DEPRECATION'] = '1'  # Silence Tk deprecation warnings on macOS
warnings.simplefilter('ignore')

# Configure matplotlib for macOS
plt.style.use('dark_background')
plt.rcParams['toolbar'] = 'None'  # Hide toolbar for cleaner look

###########CONFIGURE HERE###########

ColorZ = 1.65  # Z-score in the QByte bitstream where colors change
RotZ = 1.85  # Z-score in the QByte bitstream where rotation occurs

DotSize = 4444
wordsize = 36
Default_Marker = 'o'  # for a full list: https://matplotlib.org/stable/api/markers_api.html

NEDspeed = 250  # Number of bytes to stream from the RNG each second
RandomSrc = 'prng'  # Using pseudo-random number generator
SupHALO = True  # Set to 'True' for full (8 bitstream) QByte processing
TurboUse = False  # Set to False since we're using regular TrueRNG, not TurboRNG
UseConcurrentReading = False  # Set to True to enable concurrent RNG reading

IPFS_Estuary = True  # if RandomSrc = 'ipfs', 'True' will pull from Estuary, 'False' will pull from web3.storage

Genome = False  # set to 'True' to XOR with genome from 23 and me data file (beta feature). Turns nucleotide information (A,G,C,T) into bits that factor in to the QByte output.
GenomeSrc = 'GenomeSample.txt'  # Genome source data (this is where you can upload your DNA file from 23 and Me), ignored if Genome = 'False'

MaxFileTime = 600  # number of seconds of data to store to an individual output file
PushEstuary = False  # uploads data to Estuary at MaxFileTime interval, requires curl. REQUIRED config -> NEDspeed=250, SupHALO=True, TurboUse=True. Any RandomSrc may be used.
EstuaryCollection = 'd0e46d0d-7e4c-4bce-8401-ee1a10b89f3d'  # 'bfffcaab-d302-4bab-b0ed-552e450a2dc9'

autofreq = 600  # how often to switch view in seconds if ran in 'auto' mode

OutputImgs = False#Runs stable diffusion
ImgTime = 900#frequency to run Stable Diffusion
Max_Words = 3#Maximum number of words for Stable Diffusion prompt
STABLE_DIFFUSION_DIR = os.path.expanduser('~/stable-diffusion')#Path to working Stable Diffusion
Default_Prompt = 'hypercube algorithmic language oracle'#Prompt for Stable Diffusion if no words are generated
Default_Word = 'QBYTE'  # Default word shown when no coherence is detected

###########END USER CONFIGURATION###########

# Auto-detect TrueRNG devices if available
def detect_trng_devices():
    """Auto-detect TrueRNG devices and configure accordingly"""
    global RandomSrc, TurboUse
    
    ports_available = list(list_ports.comports())
    trng_ports = [p for p in ports_available if p[1].startswith("TrueRNG")]
    
    if trng_ports:
        logger.info(f"Found {len(trng_ports)} TrueRNG device(s)")
        RandomSrc = 'trng'
        turbo_ports = [p for p in trng_ports if 'pro' in p[1].lower()]
        if turbo_ports:
            logger.info("TurboRNG Pro detected")
            TurboUse = True
        return True
    else:
        logger.info("No TrueRNG devices detected, using pseudo-random number generator")
        RandomSrc = 'prng'
        TurboUse = False
        return False

# Check if automatic device detection is enabled
try:
    # Only attempt auto-detection if RandomSrc is set to 'trng'
    if RandomSrc == 'trng':
        detect_trng_devices()
except Exception as e:
    logger.warning(f"Error detecting TrueRNG devices: {str(e)}. Falling back to PRNG mode.")
    RandomSrc = 'prng'
    TurboUse = False

# Check for command line arguments
try:
    mType = sys.argv[1]#static,auto,nye
except:
    mType = 'static'

try:
    Rmks = sys.argv[2]#remarks
except:
    Rmks = '_'

# Print system information
logger.info(f"Running QByte on {platform.system()} {platform.release()}")
logger.info(f"Python version: {platform.python_version()}")
logger.info(f"Configuration: Mode={mType}, RandomSrc={RandomSrc}, TurboUse={TurboUse}, SupHALO={SupHALO}")

outpath = os.getcwd()
if os.path.exists('%s/dataout'%outpath)==False:
    subprocess.check_output('mkdir dataout', shell=True)

os.chdir('%s'%outpath)

TurboSpeed = NEDspeed

if RandomSrc=='prng':
    HALO = False
else:
    HALO = True

starttime = int(time.time()*1000)
outfile = open('%s/dataout/QB_%d_0_%s.txt'%(outpath,int(starttime/1000),Rmks),'w')
cmtfile = open('%s/dataout/QB_%d_%s_C.txt'%(outpath,int(starttime/1000),Rmks),'w')
imgfile = open('%s/dataout/QB_%d_%s_SD.txt'%(outpath,int(starttime/1000),Rmks),'w')

outfile.write('ColorZ: %f RotZ: %f RNG params: %s %s %s\n'%(ColorZ,RotZ,RandomSrc,HALO,TurboUse))

if SupHALO==True:
    NumNeds = 8
else:
    NumNeds = 4

DayStarted = starttime - (starttime%86400000)
StartXT = (starttime-DayStarted)/3600000

EX = NEDspeed*4
ColorThres = ColorZ * ((NEDspeed*8*0.25)**0.5)
RotThres = RotZ * ((NEDspeed*8*0.25)**0.5)

ActionNumC = math.ceil((ColorZ*((8*NEDspeed*0.25)**0.5))+(4*NEDspeed))
Pmod_Color = (scipy.stats.binom((NEDspeed*8),0.5).sf(ActionNumC-1))*2
ActionNumR = math.ceil((RotZ*((8*NEDspeed*0.25)**0.5))+(4*NEDspeed))
Pmod_Rot = (scipy.stats.binom((NEDspeed*8),0.5).sf(ActionNumR-1))*2

ax1s_zoom=[]
ax1sN_zoom=[]
Rstd_zoom=[]
Mstd_zoom=[]

for a in range (0,60):
    ax1s_zoom.append(((a*NEDspeed*8*0.25)**0.5)*1.96)
    ax1sN_zoom.append(((a*NEDspeed*8*0.25)**0.5)*-1.96)
    Rstd_zoom.append(((a*Pmod_Rot*(1-Pmod_Rot))**0.5)*1.65)
    Mstd_zoom.append(((a*Pmod_Color*(1-Pmod_Color))**0.5)*1.65)

IpfsIdx = [0]
MetaIdx = [0]

def NewIPFS():
    
    if IPFS_Estuary == True:
        estuary_json = subprocess.check_output('curl -X GET -H "Authorization: Bearer EST99cd9b05-5075-47b4-9897-f702f2e2ba2dARY" https://api.estuary.tech/collections/content?coluuid=%s'%EstuaryCollection, shell=True)
        estuary_arr = json.loads(estuary_json)
        latest_cid = estuary_arr[-1]["cid"]
        data = 'https://%s.ipfs.dweb.link'%latest_cid
    else:
        data = 'https://bafybeievaadn5wv7xlxdto5m7nqn34q7nzdk5x4fpdh4sogrx4xkdg5ad4.ipfs.dweb.link/short/NEDpredata_%d.txt'%IpfsIdx[0]
    
    print('pulling data from %s'%data)
    
    uClient = uReq(data)
    page_html = str(uClient.read())
    uClient.close()
    sepfile = page_html.split('\\n')
    
    
    MetaXX=[]
    for a in range (0,len(sepfile)-1):
        if a==0:
            xandy = sepfile[a][2:].split(',')
        else:
            xandy = sepfile[a].split(',')
        
        if len(xandy)>5:

            uNed=[]
            for b in range (0,len(xandy)-2):
                uNed.append(int(xandy[b]))
            
            MetaXX.append(uNed)
        
    IpfsIdx[0] += 1

    print(np.shape(MetaXX))

    

    return MetaXX

if RandomSrc=='ipfs':
    
    MetaNED = NewIPFS()
    

def GrabIPFS():
    if MetaIdx[0]>=len(MetaNED):
        xNED = NewIPFS()
        for a in range (0,len(xNED)):
            MetaNED[a] = xNED[a]
            
        MetaIdx[0] = 0
    
    grabbed = MetaNED[MetaIdx[0]]
    MetaIdx[0] += 1
    return grabbed
    
####

plt.style.use('dark_background')
#plt.grid([False])
fig = plt.figure(1,constrained_layout=True)
gs = fig.add_gridspec(3,2)
ax1 = fig.add_subplot(gs[:,0], projection='3d')
ax2 = fig.add_subplot(gs[0,1])
ax3 = fig.add_subplot(gs[1,1])
ax4 = fig.add_subplot(gs[2,1])
ax4t = ax4.twinx()

city = LocationInfo(latitude=37.7,longitude=-122.2)

riprise=[]
ripset=[]

zoomsto = [1]
viewsto = [3]
viewlong = [0]
entsto = [1]
SsnCt = [0]

for a in range (0,10):

    srise = sunrise(city.observer, date=datetime.datetime.now()+datetime.timedelta(days=a))
    sset = sunset(city.observer, date=datetime.datetime.now()+datetime.timedelta(days=a))
    riprise.append((srise.hour+(srise.minute/60))+(24*a))
    ripset.append((sset.hour+(sset.minute/60))+(24*a))
    
alltypes = ['hypercube','sphere','pyramid','AEM','quad','star']

def FillNode(x1,y1,x2,y2,filler_dist):
    nodedist = (((x2-x1)**2)+((y2-y1)**2))**0.5
    n_fillers = int(nodedist/filler_dist)

    filler_x=[]
    filler_y=[]

    for a in range (0,n_fillers):
        frac = (a+0.5)/n_fillers
        const_x = frac*(x2-x1)
        const_y = frac*(y2-y1)

        filler_x.append(x1+const_x)
        filler_y.append(y1+const_y)

    return filler_x,filler_y

def MkShape(shp):
    if shp == 'hypercube':
        
        WM_ll = 1.4
        WM_ul = 4.1
        
        ShapeC = []
        Node=[]
        sNode = []
        
        readFile = open('%s/HypercubeExt.txt'%outpath,'r')
        sepfile = readFile.read().split('\n')
        for a in range (0,len(sepfile)):
            xandy = sepfile[a].split('\t')
            ShapeC.append([int(xandy[0])-4,int(xandy[1])-4,int(xandy[2])-4])
            Node.append(int(xandy[3]))
            if int(xandy[3])==1:
                sNode.append([int(xandy[0])-4,int(xandy[1])-4,int(xandy[2])-4])
                
    if shp == 'sphere' or shp == 'nye':
        
        WM_ll = 1.4
        WM_ul = 1.42
            
        ShapeC = []
        xxx=[]
        yyy=[]
        zzz=[]
        for a in range (0,12):
            theta = 2*np.pi*(a/12)
            numphi = int(np.abs(round(np.sin(theta)*12)))
            for b in range (0,numphi):
                phi = ((2*np.pi)/numphi)*b
                x = np.sin(theta)*np.cos(phi)
                y = np.sin(theta)*np.sin(phi)
                z = np.cos(theta)
                ShapeC.append([x,y,z])
                xxx.append(x)
                yyy.append(y)
                zzz.append(z)
        
        sNode = []; idxs=[]
        idx = np.argmin(xxx)
        idxs.append(idx)
        sNode.append(ShapeC[idx])
        idx = np.argmax(xxx)
        idxs.append(idx)
        sNode.append(ShapeC[idx])
        idx = np.argmin(yyy)
        idxs.append(idx)
        sNode.append(ShapeC[idx])
        idx = np.argmax(yyy)
        idxs.append(idx)
        sNode.append(ShapeC[idx])
        idx = np.argmin(zzz)
        idxs.append(idx)
        sNode.append(ShapeC[idx])
        idx = np.argmax(zzz)
        idxs.append(idx)
        sNode.append(ShapeC[idx])
        
        Node=[]
        for a in range (0,len(ShapeC)):
            if a in idxs:
                Node.append(1)
            else:
                Node.append(0)
                
    if shp == 'pyramid':
        
        WM_ll = 0.7
        WM_ul = 2.1      
        
        ShapeC = []
        x = [1,2,3,4,5,0.5,0.5,0.5,0.5,0.5,1,2,3,4,5,5.5,5.5,5.5,5.5,5.5,2,3,4,1.5,1.5,1.5,2,3,4,4.5,4.5,4.5,2.5,3.5,3,3]
        y = [0.5,0.5,0.5,0.5,0.5,1,2,3,4,5,5.5,5.5,5.5,5.5,5.5,1,2,3,4,5,1.5,1.5,1.5,2,3,4,4.5,4.5,4.5,2,3,4,3,3,2.5,3.5]
        z = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2,2,2,2,2,2,3,3,3,3]
        z = np.array(z)-0.5
        
        Node = [1,0,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1,1,0,1,1,0,1,1,0,1,1,1,1,1,1,0,1,0,1,0,0,0,0,0,1,0,1,0,1,0,0,0,0,0,1,0,1,0,1,1]
        
        plusX = [1,2,3,4,5,1,2,3,4,5,1,2,3,4,5,1,2,3,4,5,1,2,3,4,5]
        plusY = [1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,5,5,5,5,5]
        plusZ = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        
        for a in range (0,len(x)):
            ShapeC.append([x[a],y[a],z[a]])
        for a in range (0,len(plusX)):
            ShapeC.append([plusX[a],plusY[a],plusZ[a]])
        ShapeC.append([3,3,3])    
    
        sNode = []
        for a in range (0,len(ShapeC)):
            if Node[a]==1:
                sNode.append(ShapeC[a])
    
    if shp=='AEM':
        
        WM_ll = 0.6
        WM_ul = 0.64    
        
        ShapeC = []
        for a in range (0,10):
            rads = (a/10)*2*np.pi
            ShapeC.append([np.cos(rads),np.sin(rads),0])
        sNode = ShapeC
        Node = [1,1,1,1,1,1,1,1,1,1]
        
    if shp=='quad':
        
        WM_ll = 1.4
        WM_ul = 2.1  
        
        ShapeC = [[2,1,0],[2,5,0],[4,1,0],[4,5,0],[1,2,0],[1,4,0],[5,2,0],[5,4,0]]
        sNode = ShapeC
        Node = [1,1,1,1,1,1,1,1]

    if shp=='star':

        WM_ll = 1.85
        WM_ul = 1.95

        x = [-0.807,0.287,0.318,-0.807,1]
        y = [-0.59,0.958,-0.948,0.59,0.016]

        sNode=[]
        ShapeC=[]
        Node=[]
        for a in range (0,len(x)):
            sNode.append([x[a],y[a],0])
            ShapeC.append([x[a],y[a],0])
            Node.append(1)
        


        for a in range (0,len(x)):

            ll = a
            if a==len(x)-1:
                ul = 0
            else:
                ul = a+1

            more_x,more_y = FillNode(x[ll],y[ll],x[ul],y[ul],0.1)
            for b in range (0,len(more_x)):
                xf=more_x[b]
                yf=more_y[b]

                ShapeC.append([xf,yf,0])
                Node.append(0)
    
    infile = 'sim_%s'%shp

    SimMI = []    
    readFile = open('%s/%s.txt'%(outpath,infile),'r')
    sepfile = readFile.read().split('\n')
    for a in range (0,len(sepfile)-1):
        SimMI.append(float(sepfile[a]))
    Msorted = sorted(SimMI)
    
    
    Dist=[]
    WM = np.zeros((len(sNode),len(sNode)))
    ShapeCt = 0
    Kct = 0
    for a in range (0,len(ShapeC)):
        xm = []
        for b in range (0,len(sNode)):
            dd = (((ShapeC[a][0]-sNode[b][0])**2)+((ShapeC[a][1]-sNode[b][1])**2)+((ShapeC[a][2]-sNode[b][2])**2))**0.5
            if dd>0:
                xm.append(1/(dd**3))
            else:
                xm.append(999)
        if np.amax(xm)==999:#checks if we're on a sNode
            
            for b in range (0,len(sNode)):
                dd = (((ShapeC[a][0]-sNode[b][0])**2)+((ShapeC[a][1]-sNode[b][1])**2)+((ShapeC[a][2]-sNode[b][2])**2))**0.5
                if WM_ll<=dd<=WM_ul:#sqrt of 2 to 4 but within tolerance to allow floating point errors
                    WM[ShapeCt,b] = 1
                    Kct += 1
            ShapeCt += 1
                    
        Dist.append(xm)
    
    return ShapeC,sNode,Node,Msorted,Dist,WM
    
def newfile(n):
    global outfile
    outfile.close()

    if PushEstuary==True:
        try:
            estout = subprocess.check_output('curl -X POST https://shuttle-5.estuary.tech/content/add -H "Authorization: Bearer EST99cd9b05-5075-47b4-9897-f702f2e2ba2dARY" -H "Accept: application/json" -H "Content-Type: multipart/form-data" -F "data=@%s/QB_%d_%d_%s.txt"'%(outpath,int(starttime/1000),n-1,Rmks), shell=True)
            estjson = json.loads(estout)
            cid = estjson["cid"]
            eststr = 'curl -X POST https://api.estuary.tech/collections/add-content -d' + " '{ " + '"contents": [], "cids": ["' + cid + '"], "coluuid": "%s" }'%EstuaryCollection + "' -H " + '"Content-Type: application/json" -H "Authorization: Bearer EST99cd9b05-5075-47b4-9897-f702f2e2ba2dARY"'
            os.system('%s'%eststr)
        except:
            print("Estuary Upload %d_%d_%s Failed"%(int(starttime/1000),n-1,Rmks))

    outfile = open('%s/dataout/QB_%d_%d_%s.txt'%(outpath,int(starttime/1000),n,Rmks),'w')

def printInput():
    inp = inputtxt.get(1.0, "end-1c")
    cmtfile.write('%d,%s\n'%(int(time.time()*1000),inp))
    cmtfile.flush()
    os.fsync(cmtfile.fileno())
    frame.wm_withdraw()
    inputtxt.delete(1.0,"end-1c")
    
def kill(self):
    ani.event_source.stop()
    outfile.close()
    cmtfile.close()
    imgfile.close()
    sys.exit()

def comment(self):
    frame.wm_deiconify()
    frame.mainloop()
    
def zoom(self):
    tmp = zoomsto[0]
    if tmp==0:
        zoomsto[0] = 1
    else:
        zoomsto[0] = 0

def show_diffusion(self):

    if OutputImgs==False:
        print("No images to show. Please set OutputImgs=True and provide a valid Stable Diffusion path.")
    
    else:

        latest_file = sorted(os.listdir('%s/outputs/txt2img-samples'%STABLE_DIFFUSION_DIR))[-2]

        plt.figure(2)
        img = mpimg.imread('%s/outputs/txt2img-samples/%s'%(STABLE_DIFFUSION_DIR,latest_file))
        imgplot = plt.imshow(img)
        plt.show()
        

def autoview():
    tmp = viewsto[0]
    if tmp==(len(alltypes)-1):
        viewsto[0] = 0
    else:
        viewsto[0] += 1
        
    mShapeC[viewsto[0]] = MkShape(alltypes[viewsto[0]])[0]
    
    viewlong.append(viewsto[0])
    
    AC = Bulk()
    AimColors.append(GetColors(AC[0],viewsto[0])[0])
    AC = Bulk()
    AimColors.append(GetColors(AC[0],viewsto[0])[0])
    
    outfile.write('switch view to %d\n'%viewsto[0])
        
def view(self):
    autoview()

def entrain(self):
    global ult_t
    global MaxFileTime
    SsnCt[0]+=1
    tmp = entsto[0]
    if tmp==0:
        entsto[0] = 1
        newfile(int(len(ult_t)/MaxFileTime))
        bent.color = '0.5'
    else:
        entsto[0] = 0
        newfile(-1*int((SsnCt[0]/2)+0.5))
        bent.color = 'red'
    
    
    

    
frame = tk.Tk()
frame.title("eh?")
frame.geometry('400x50')
inputtxt = tk.Text(frame,height = 1,width = 35)
inputtxt.pack()
printButton = tk.Button(frame,text = "Submit", command = printInput)
printButton.pack()

axcmt = plt.axes([0.05, 0.05, 0.06, 0.05])
bcmt = Button(axcmt, 'comment', color = '0.5', hovercolor='0.8')
bcmt.on_clicked(comment)

axkil = plt.axes([0.12, 0.05, 0.06, 0.05])
bkil = Button(axkil, 'stop', color = '0.5', hovercolor='0.8')
bkil.on_clicked(kill)

axzoom = plt.axes([0.19, 0.05, 0.06, 0.05])
bzoom = Button(axzoom, 'zoom', color = '0.5', hovercolor='0.8')
bzoom.on_clicked(zoom)

axview = plt.axes([0.26, 0.05, 0.06, 0.05])
bview = Button(axview, 'view', color = '0.5', hovercolor='0.8')
bview.on_clicked(view)

axent = plt.axes([0.33, 0.05, 0.06, 0.05])
bent = Button(axent, 'session', color = '0.5', hovercolor='0.8')
bent.on_clicked(entrain)

aximg = plt.axes([0.40, 0.05, 0.06, 0.05])
bimg = Button(aximg, 'latest img', color = '0.5', hovercolor='0.8')
bimg.on_clicked(show_diffusion)


AllLO=[]
Readfile=open('%s/Wordbank.txt'%outpath,encoding='latin-1')
Lines=Readfile.read().split('\n')
for line in range(0,len(Lines)):
    AllLO.append(Lines[line])


if Genome==True:
    GenomeBin = ['CC','CG','CA','CT','GC','GG','GA','GT','AC','AG','AA','AT','TC','TG','TA','TT']
    Readfile = open('%s/%s'%(outpath,GenomeSrc),'r')
    sepfile = Readfile.read().split('\n')
    PreSeq = []
    for a in range (21,len(sepfile)):
        for b in range (0,len(GenomeBin)):
            if GenomeBin[b] in sepfile[a]:
                PreSeq.append(b)
    GenomeBits = []
    for a in range (0,len(PreSeq),2):
        GenomeBits.append((PreSeq[a]*16)+PreSeq[a+1])

    # print(np.amin(GenomeBits),np.amax(GenomeBits),len(GenomeBits))
    



if RandomSrc=='trng':
    # Initialize variables
    rngcomports = []
    ser = []
    turbocom = None
    turboser = None
    
    try:
        ports_available = list(list_ports.comports())
        
        # Look for TrueRNG devices
        logger.info("Scanning for TrueRNG devices...")
        
        for temp in ports_available:
            if HALO and temp[1].startswith("TrueRNG"):
                if 'pro' in temp[1].lower():
                    logger.info(f"Found TurboRNG Pro device: {temp}")
                    turbocom = str(temp[0])
                else:
                    logger.info(f"Found TrueRNG device: {temp}")
                    rngcomports.append(str(temp[0]))
            elif not HALO and temp[1].startswith("TrueRNG"):
                logger.info(f"Found TrueRNG device: {temp}")
                turbocom = str(temp[0])
        
        # Handle device initialization
        if HALO:
            if not rngcomports:
                logger.warning("No regular TrueRNG devices found. Using PRNG fallback for regular streams.")
                # Create dummy serial objects for PRNG
                for _ in range(8):
                    ser.append(None)
            else:
                for a in range(len(rngcomports)):
                    try:
                        new_ser = serial.Serial(port=rngcomports[a], timeout=10)
                        ser.append(new_ser)
                        logger.info(f"Initialized TrueRNG device: {rngcomports[a]}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize TrueRNG device {rngcomports[a]}: {str(e)}")
                        ser.append(None)
                
                # Fill any missing device slots with None
                while len(ser) < 8:
                    ser.append(None)
                    
        # Handle TurboRNG initialization
        if TurboUse:
            if not turbocom:
                logger.warning("No TurboRNG Pro device found. Disabling TurboRNG feature.")
                TurboUse = False
            else:
                try:
                    turboser = serial.Serial(port=turbocom, timeout=10)
                    logger.info(f"Initialized TurboRNG Pro device: {turbocom}")
                except Exception as e:
                    logger.warning(f"Failed to initialize TurboRNG Pro device: {str(e)}")
                    TurboUse = False
                    turboser = None
        
        # Setup serial ports
        for a in range(len(ser)):
            if ser[a] is not None:
                try:
                    if not ser[a].isOpen():
                        ser[a].open()
                    ser[a].setDTR(True)
                    ser[a].flushInput()
                    logger.info(f"Opened and configured TrueRNG device: {rngcomports[a%len(rngcomports)]}")
                except Exception as e:
                    logger.warning(f"Error configuring TrueRNG device {a}: {str(e)}")
                    ser[a] = None
        
        if TurboUse and turboser is not None:
            try:
                if not turboser.isOpen():
                    turboser.open()
                turboser.setDTR(True)
                turboser.flushInput()
                logger.info("Opened and configured TurboRNG Pro device")
            except Exception as e:
                logger.warning(f"Error configuring TurboRNG Pro device: {str(e)}")
                TurboUse = False
                turboser = None
        
        sys.stdout.flush()
        
    except Exception as e:
        logger.error(f"Error initializing TrueRNG devices: {str(e)}")
        logger.info("Falling back to PRNG mode")
        RandomSrc = 'prng'
        HALO = False
        TurboUse = False
        rngcomports = ['pseudoRNG']
        ser = [None]
        
    # Verify we have enough working devices
    working_devices = sum(1 for s in ser if s is not None)
    if RandomSrc == 'trng' and working_devices == 0:
        logger.warning("No working TrueRNG devices found. Switching to PRNG mode.")
        RandomSrc = 'prng'
        HALO = False
        TurboUse = False
        rngcomports = ['pseudoRNG']
        ser = [None]
        
else:
    # Not using hardware RNG
    rngcomports = ['pseudoRNG']
    ser = [None]



def M2P(MIv,typidx):
    idx = 0
    for a in range (0,len(mMsorted[typidx])):
        if mMsorted[typidx][a]>MIv:
            idx += 1
    if idx==0:
        idx += 1
    p_i = idx/1000000
    #print(idx,MIv,np.amin(Msorted),np.amax(Msorted))
    return p_i
    
def Color2Prompt (Cwords,Cweights,x_words):
    wordlist = [Lx for _,Lx in sorted(zip(Cweights,Cwords),reverse=True)]
    
    if len(wordlist)>x_words:
        maxuse = x_words
    else:
        maxuse = len(wordlist)

    wordprompt = ''
    for a in range (0,maxuse):
        wordprompt += '%s '%wordlist[a]
    return wordprompt




def Bulk():
    global UseConcurrentReading
    global Bird  # Make Bird global so we can persist it between calls
    pct = []
    allsums = []
    
    # Initialize Bird on first call
    if not hasattr(Bulk, 'current_word'):
        Bulk.current_word = Default_Word
    
    # Initialize data arrays for all possible devices
    for a in range(0, 9):
        pct.append([])
        
    # Special handling for PRNG mode to ensure proper random data
    if RandomSrc == 'prng' and not UseConcurrentReading:
        # Fill arrays with proper random integers for PRNG mode
        for a in range(0, NumNeds):
            pct[a] = list(np.random.randint(0, 256, NEDspeed))
        if TurboUse:
            pct[8] = list(np.random.randint(0, 256, TurboSpeed))
    
    # Handle concurrent reading mode for hardware RNG    
    if not hasattr(Bulk, 'rng_reader') and UseConcurrentReading and RandomSrc == 'trng':
        try:
            Bulk.rng_reader = RNGReader(num_devices=len(ser))
            Bulk.rng_reader.start_readers(ser, NEDspeed)
            logger.info("Started concurrent RNG reader")
        except Exception as e:
            logger.error(f"Failed to start concurrent reader: {str(e)}")
            logger.info("Falling back to sequential reading")
            UseConcurrentReading = False
        
    # Process data using concurrent reader
    if UseConcurrentReading and RandomSrc == 'trng':
        try:
            # Get data from all devices using concurrent reader
            device_data = Bulk.rng_reader.get_data()
            
            # Fallback to sequential if we don't have enough data
            if len(device_data) < NumNeds:
                logger.warning(f"Insufficient data from devices ({len(device_data)}/{NumNeds}), falling back to sequential")
                Bulk.__dict__.pop('rng_reader', None)  # Remove reader to force reinitialization
                UseConcurrentReading = False  # Temporarily disable concurrent reading
                return Bulk()  # Retry with sequential reading
                
            # Process TurboRNG if enabled
            if TurboUse:
                try:
                    logger.debug("Starting TurboRNG read", extra={'device_id': 'turbo'})
                    turboser.flushInput()
                    supernode = turboser.read(TurboSpeed)
                    logger.debug(f"TurboRNG read complete - received {len(supernode)} bytes", extra={'device_id': 'turbo'})
                except Exception as e:
                    logger.error(f"TurboRNG read failed: {str(e)}", extra={'device_id': 'turbo'})
                    logger.info("Using random data as fallback for TurboRNG")
                    supernode = np.random.randint(0,256,TurboSpeed)
                    
                tempsum = 0
                for b in range(0, len(supernode)):
                    outfile.write('%d,'%(supernode[b]))
                    pct[8].append(supernode[b])
                    strnode = str(bin(256+int(supernode[b])))[3:]
                    tempsum += sum(int(bit) for bit in strnode)
                outfile.write('%d,T\n'%(int(time.time()*1000)))
                allsums.append(tempsum)
                
            # Process data from regular RNG devices
            for data in device_data:
                device_idx = int(data.device_id[3:])  # Extract index from RNGx device_id
                node = data.data
                tempsum = 0
                for mm in range(0, NEDspeed):
                    outfile.write('%d,'%(node[mm]))
                    pct[device_idx].append(node[mm])
                    strnum = bin(256+node[mm])[3:]
                    tempsum += sum(int(bit) for bit in strnum)
                
                allsums.append(tempsum)
                outfile.write('%d,%s\n'%(int(time.time()*1000), rngcomports[device_idx%len(ser)]))
                
            # Ensure all device arrays are initialized with data
            for i in range(NumNeds):
                if not pct[i]:  # If array is empty
                    pct[i] = [0] * NEDspeed  # Fill with zeros
                    logger.warning(f"Missing data from device {i}, using zeros")
        except Exception as e:
            logger.error(f"Error in concurrent reading: {str(e)}")
            logger.info("Falling back to sequential reading")
            UseConcurrentReading = False
            # Initialize with random data to ensure we can continue
            for i in range(NumNeds):
                if not pct[i]:  # If array is empty
                    pct[i] = list(np.random.randint(0, 256, NEDspeed))
                
    # Sequential implementation (fallback for concurrent mode or default for non-concurrent mode)
    if not UseConcurrentReading or RandomSrc != 'trng':
        # Handle TurboRNG if enabled and using hardware
        if TurboUse and RandomSrc == 'trng':
            try:
                logger.debug("Starting TurboRNG read", extra={'device_id': 'turbo'})
                turboser.flushInput()
                supernode = turboser.read(TurboSpeed)
                logger.debug(f"TurboRNG read complete - received {len(supernode)} bytes", extra={'device_id': 'turbo'})
            except Exception as e:
                logger.error(f"TurboRNG read failed: {str(e)}", extra={'device_id': 'turbo'})
                logger.info("Using random data as fallback for TurboRNG")
                supernode = np.random.randint(0,256,TurboSpeed).tobytes()
                
            # Process TurboRNG data
            tempsum = 0
            for b in range(0, len(supernode)):
                try:
                    if isinstance(supernode[b], int):
                        byte_val = supernode[b]
                    else:
                        byte_val = supernode[b] if isinstance(supernode[b], int) else ord(supernode[b])
                except (IndexError, TypeError):
                    byte_val = np.random.randint(0, 256)
                    
                outfile.write('%d,'%(byte_val))
                pct[8].append(byte_val)
                
                strnode = str(bin(256+byte_val))[3:]
                tempsum += sum(int(bit) for bit in strnode)
            outfile.write('%d,T\n'%(int(time.time()*1000)))
            
            allsums.append(tempsum)
            
        # Handle IPFS data source
        elif RandomSrc == 'ipfs':
            supernode = GrabIPFS()
            
            # Process IPFS data
            tempsum = 0
            for b in range(0, len(supernode)):
                outfile.write('%d,'%(supernode[b]))
                pct[8].append(supernode[b])
                
                strnode = str(bin(256+int(supernode[b])))[3:]
                tempsum += sum(int(bit) for bit in strnode)
            outfile.write('%d,T\n'%(int(time.time()*1000)))
            
            allsums.append(tempsum)
            
        # Special handling for PRNG to use pre-populated arrays for Turbo
        elif RandomSrc == 'prng' and TurboUse:
            # Use the pre-populated data from pct[8]
            tempsum = 0
            for b in range(0, len(pct[8])):
                outfile.write('%d,'%(pct[8][b]))
                strnode = str(bin(256+pct[8][b]))[3:]
                tempsum += sum(int(bit) for bit in strnode)
            outfile.write('%d,T\n'%(int(time.time()*1000)))
            
            allsums.append(tempsum)
        
        # Process regular RNG device data - but skip for PRNG mode since we already populated the arrays
        for a in range(0, NumNeds):
            device_id = f"RNG{a}"
            
            # If using PRNG, we already filled the arrays, so just write to file
            if RandomSrc == 'prng':
                tempsum = 0
                for mm in range(0, NEDspeed):
                    outfile.write('%d,'%(pct[a][mm]))
                    strnum = bin(256 + pct[a][mm])[3:]
                    tempsum += sum(int(bit) for bit in strnum)
                
                allsums.append(tempsum)
                outfile.write('%d,%s\n'%(int(time.time()*1000), "PRNG"))
                continue
            
            # Read from hardware if using TRNG
            if RandomSrc == 'trng':
                try:
                    # Only try to read from hardware if we have devices connected
                    if len(ser) > 0:
                        logger.debug(f"Starting read from device {rngcomports[a%len(ser)]}", extra={'device_id': device_id})
                        ser[a%len(ser)].flushInput()
                        node = ser[a%len(ser)].read(NEDspeed)
                        logger.debug(f"Read complete - received {len(node)} bytes", extra={'device_id': device_id})
                    else:
                        # No devices connected, use random data
                        raise Exception("No TrueRNG devices connected")
                except Exception as e:
                    logger.warning(f"Device read failed: {str(e)}. Using random data.", extra={'device_id': device_id})
                    node = np.random.randint(0, 256, NEDspeed).tobytes()
            # Use appropriate data source based on configuration
            elif RandomSrc == 'ipfs':
                node = GrabIPFS()
            else:
                # Fallback to PRNG for any unhandled case
                node = np.random.randint(0, 256, NEDspeed).tobytes()
           
            # Process the data
            tempsum = 0
            for mm in range(0, NEDspeed):
                try:
                    val = node[mm]
                    if isinstance(val, int):
                        byte_val = val
                    else:
                        byte_val = val if isinstance(val, int) else ord(val)
                except (IndexError, TypeError):
                    # Handle case where node is shorter than expected or wrong type
                    logger.warning(f"Data error at index {mm}, using random value", extra={'device_id': device_id})
                    byte_val = np.random.randint(0, 256)
                    
                outfile.write('%d,'%(byte_val))
                strnum = bin(256 + byte_val)[3:]
                pct[a].append(byte_val)
                
                tempsum += sum(int(bit) for bit in strnum)
            
            # Track entropy data
            allsums.append(tempsum)
            
            # Write device identifier
            if RandomSrc == 'trng' and len(ser) > 0:
                outfile.write('%d,%s\n'%(int(time.time()*1000), rngcomports[a%len(ser)]))
            else:
                outfile.write('%d,%s\n'%(int(time.time()*1000), "PRNG" if RandomSrc == 'prng' else RandomSrc))

    # Process the data for QByte
    x = []  # This should be NEDspeed long
    
    # Prepare data from all streams
    Pur0 = pct[0]
    Pur1 = pct[1]
    Pur2 = pct[2]
    Pur3 = pct[3]
    Pur4 = pct[4]
    Pur5 = pct[5]
    Pur6 = pct[6]
    Pur7 = pct[7]
    if TurboUse:
        PurT = pct[8]
    
    # Generate genome index if needed
    try:
        GenomeIdx = ((Pur0[0]*(256**2)) + (Pur0[1]*(256**1)) + (Pur0[2]*(256**0)))
    except (IndexError, TypeError):
        # Handle case where data is missing
        GenomeIdx = np.random.randint(0, 256**3)
        logger.warning(f"Error calculating GenomeIdx, using random value: {GenomeIdx}")

    # Process each byte of data with the QByte algorithm
    for b in range(0, len(Pur0)):
        try:
            if SupHALO:
                xA = Pur0[b]^Pur7[b]
                xB = Pur1[b]^Pur6[b]
                xC = Pur2[b]^Pur5[b]
                xD = Pur3[b]^Pur4[b]
            
                xE = xA^xD
                xF = xB^xC
            else:
                xE = Pur0[b]^Pur3[b]
                xF = Pur1[b]^Pur2[b]
            
            xG = xE^xF
            
            if TurboUse:
                xH = xG^PurT[b]
            else:
                xH = xG

            if Genome:
                GenomeIdxX = (GenomeIdx+b)%len(GenomeBits)
                xDNA = xH ^ GenomeBits[GenomeIdxX]
            else:
                xDNA = xH
            
            x.append(xDNA)
        except (IndexError, TypeError) as e:
            # Handle error in data processing
            logger.warning(f"Error processing byte {b}: {str(e)}")
            x.append(np.random.randint(0, 256))  # Use random data for this byte
    
    # Calculate bit count
    bitct = 0
    for a in range(0, len(x)):
        try:
            outfile.write('%d,' % x[a])
            strnode = str(bin(256 + int(x[a])))[3:]
            bitct += sum(int(bit) for bit in strnode)
        except (ValueError, TypeError) as e:
            # Handle error in bit counting
            logger.warning(f"Error counting bits for byte {a}: {str(e)}")
            outfile.write('0,')  # Write a placeholder
    
    outfile.write('%d,QBYTE | ' % (int(time.time()*1000)))
    
    # Flush the data to disk
    outfile.flush()
    os.fsync(outfile.fileno())
    
    # Process final bytes for word selection
    try:
        str0 = str(bin(256+int(x[-2])))[3:] + str(bin(256+int(x[-1])))[3:]
        ones = sum(int(bit) for bit in str0)

        uidx = -3
        sector = -9999
        while sector < -1:
            if x[uidx] < 252:
                sector = x[uidx]%3
            uidx -= 1
        
        LO_idx = ((sector%3)*65536)+(x[-2]*256)+x[-1]
        
        # Only update the word if we're in a coherence event
        if np.abs(bitct-EX) > ColorThres:
            try:
                Bulk.current_word = AllLO[LO_idx]
            except IndexError:
                # Handle case where LO_idx is out of range
                logger.warning(f"Invalid word index {LO_idx}, using default word")
                Bulk.current_word = Default_Word
        
        wrd = Bulk.current_word

        Z = np.abs(ones-8)

        if ones==8:
            symbol = '.0'
        if ones<8:
            symbol = '.-%d'%Z
        if ones>8:
            symbol = '.+%d'%Z
    except (IndexError, ValueError, TypeError) as e:
        # Handle errors in word selection logic
        logger.warning(f"Error in word selection: {str(e)}")
        wrd = Default_Word
        symbol = '.0'
    
    outfile.write('%s\n'%wrd)
    
    return x, bitct, symbol, wrd, allsums

maxon = 65535
def GetColors(colors,typidx):
    #colors,r1 = Bulk()
    offset = 0
    Config = []
    U=[]
    V=[]
    for lights in range (0,len(msNode[typidx])):
        slider = (colors[-1+offset]*256)+colors[-2+offset]
        uidx = -3+offset
        sector = -9999
        while sector < -1:
            if colors[uidx] < 252:
                sector = colors[uidx]%6
            uidx -= 1
            
        offset = uidx
        
        
        if sector == 0:
            R,G,B = maxon,slider,0
        if sector == 1:
            R,G,B = slider,maxon,0
        if sector == 2:
            R,G,B = 0,maxon,slider
        if sector == 3:
            R,G,B = 0,slider,maxon
        if sector == 4:
            R,G,B = slider,0,maxon
        if sector == 5:
            R,G,B = maxon,0,slider
        Config.append([R,G,B])
        
        theta = (np.pi*(1/3)*sector)+((slider/65536)*np.pi*(1/3))
        U.append(np.cos(theta))
        V.append(np.sin(theta))
        
    return Config,sector,U,V



#shape initialization:
if mType == 'nye':
    targettime = int(sys.argv[3])
RadList = []
for a in range (0,10):
    rads = (a/10)*2*np.pi
    RadList.append(rads)
BaseX = [0,6,6,0,0]
BaseY = [0,0,6,6,0]
BaseZ = [0,0,0,0,0]
Beam1x = [0,3,6]
Beam1y = [0,3,6]
Beam1z = [0,3,0]
Beam2x = [6,3,0]
Beam2y = [0,3,6]
Beam2z = [0,3,0]
pollX = [0,0]
pollY = [0,0]
pollZ = [-6,0]

mShapeC=[]
OGShapeC=[]
msNode=[]
mNode=[]
mMsorted=[]
mDist=[]
mWM=[]
for a in range (0,len(alltypes)):
    print('building %s'%alltypes[a])
    info = MkShape(alltypes[a])
    mShapeC.append(info[0])
    OGShapeC.append(info[0])
    msNode.append(info[1])
    mNode.append(info[2])
    mMsorted.append(info[3])
    mDist.append(info[4])
    mWM.append(info[5])






    
def RotateAEM(theta,typidx):
    for a in range (0,len(mShapeC[typidx])):
        mShapeC[typidx][a][0] = np.cos(RadList[a]+theta)
        mShapeC[typidx][a][1] = np.sin(RadList[a]+theta)
        RadList[a] = RadList[a]+theta
    
def Rotate(theta,axs,typidx,doall=False):
    if axs=='x':
        m0 = 2
        m1 = 0
        m2 = 1
    if axs=='y':
        m0 = 0
        m1 = 1
        m2 = 2
    if axs=='z':
        m0 = 1
        m1 = 0
        m2 = 2
    for a in range (0,len(mShapeC[typidx])):
        if (-1<=mShapeC[typidx][a][m0]<=1 and doall==False) or doall==True:
            r = ((mShapeC[typidx][a][m1]**2)+(mShapeC[typidx][a][m2]**2))**0.5
            #phi = np.arctan((ShapeC[a][1])/(ShapeC[a][0]))
            phi = math.atan2(mShapeC[typidx][a][m2],mShapeC[typidx][a][m1])
            phi += theta
            mShapeC[typidx][a][m1] = r*np.cos(phi)
            mShapeC[typidx][a][m2] = r*np.sin(phi)

def Drop(typidx):
    for a in range (0,len(mShapeC[typidx])):
        mShapeC[typidx][a][2] = mShapeC[typidx][a][2]-0.1
            
def SnapInt(typidx):
    for a in range (0,len(mShapeC[typidx])):
        mShapeC[typidx][a][0] = int(np.rint(mShapeC[typidx][a][0]))
        mShapeC[typidx][a][1] = int(np.rint(mShapeC[typidx][a][1]))
        mShapeC[typidx][a][2] = int(np.rint(mShapeC[typidx][a][2]))



ult_t=[]
Mplt=[]
Mstd=[]
Rplt=[]
Rstd=[]

Xsums=[]
QBsums=[]

ax1y=[]
ax1s=[]
ax1sN=[]  
axQB=[]  
for a in range (0,NumNeds+1):
    Xsums.append([])
    ax1y.append([])

    
    
AimColors = []
Aim_t=[]

AC = Bulk()
AimColors.append(GetColors(AC[0],viewsto[0])[0])

AC = Bulk()
AimColors.append(GetColors(AC[0],viewsto[0])[0])

Aim_t.append(len(ult_t))

Rot_t=[-999]
RotTyp=[]

MI=[]
MIt=[]

KMlog=[]
CumP=[]

ColorWords = []
ColorWeights = []

def GetI(uu,vv,typidx):
    Ksum=0.0; Kct=0; NCct=0
    for a in range (0,len(uu)):
        for b in range (0,len(uu)):
            if (mWM[typidx][a,b]==1):#detects neighboring cell, allowing for diagonal directions
                Ksum+= (((uu[a])*(uu[b]))+((vv[a])*(vv[b])))
                Kct+=1
            NCct+=1
            
    SSQ_K = len(uu)
    MORAN = ((len(uu)*Ksum)/(float(Kct)*float(SSQ_K)))
    return MORAN


def animate(i):
    
    global ColorWords
    global ColorWeights
    global Rpos  # Add global declaration
    
    Rpos = len(ult_t)-Rot_t[-1]  # Initialize Rpos
    
    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()
    ax4t.clear()



    if len(ult_t)%MaxFileTime==0 and len(ult_t)>0 and entsto[0]==1:
        newfile(int(len(ult_t)/MaxFileTime))

    if OutputImgs==True and len(ult_t)%ImgTime==0 and len(ult_t)>0:
        
        myprompt = Color2Prompt(ColorWords,ColorWeights,Max_Words)

        if myprompt == '':
            myprompt = Default_Prompt

        print("generating AI image for prompt: %s"%myprompt)

        present = os.getcwd()
        os.chdir('%s'%STABLE_DIFFUSION_DIR)

        output_str = subprocess.check_output(
            [
                'python', 'scripts/txt2img.py','--prompt', '"%s"'%myprompt, '--plms', '--H', '512', '--W', '512', '--n_samples', '1'
            ],
                
            stderr=subprocess.STDOUT
        )

        latest_file = sorted(os.listdir('%s/outputs/txt2img-samples'%STABLE_DIFFUSION_DIR))[-2]
        imgfile.write('TIME: %d | FILE: %s | PROMPT: %s\n'%(int(time.time()*1000),latest_file,myprompt))

        os.chdir(present)

        ColorWords = []
        ColorWeights = []

    now_p = time.time()
    now = now_p-(starttime/1000)
    
    reds=[]
    greens=[]
    blues=[]
    

    
    if mType=='auto':
        if len(ult_t)%autofreq==0 and len(ult_t)>0:
            autoview()
    
    useview = viewsto[0]
    
    Type = alltypes[useview]
    

    
    if mType=='nye':
        timetodest = targettime - now_p
    else:
        timetodest = None
        
    hrOfD = int((now_p%86400)/3600)
    mnOfD = int((now_p%3600)/60)
    scOfD = int(now_p%60)
    fOfD = str(now_p%1) + '000000'
    microf = fOfD[2:8]
    
    hrRun = int((now)/3600)
    mnRun = int((now%3600)/60)
    scRun = int(now%60)
    
    AC = Bulk()
    t_symbol = AC[2]
    Bird = AC[3]
    
    for a in range (0,len(AC[4])):
        Xsums[a].append(AC[4][a])
    
    
    
    pos = len(ult_t)-Aim_t[-1]
    #print('op enter %d'%pos)
    
    if (np.abs(AC[1]-EX)>ColorThres) and (pos>10):
        aim = GetColors(AC[0],useview)
        
        AimColors.append(aim[0])
        Aim_t.append(len(ult_t))
        #print('spike i %d'%pos)
        
        ival = GetI(aim[2],aim[3],useview)
        tmp_p = M2P(ival,useview)
        pval = 1/tmp_p

        x_red = []
        x_green = []
        x_blue = []
        for a in range (0,len(aim[0])):
            x_red.append(aim[0][a][0])
            x_green.append(aim[0][a][1])
            x_blue.append(aim[0][a][2])
        outfile.write('color change,%f,%d,%d,%d,%d,%f\n'%(ival,useview,int(np.average(x_red)/256),int(np.average(x_green)/256),int(np.average(x_blue)/256),pval))
        MI.append(pval)
        MIt.append((int(now_p*1000)-DayStarted)/3600000)
        KMlog.append(np.log(tmp_p))
        CumP.append(scipy.stats.chi2.sf((np.sum(KMlog)*-2),(2*len(MIt))))

        ColorWords.append(Bird)
        ColorWeights.append(pval)
        
        #print(ival)
        
        
        

        
    pos = len(ult_t)-Aim_t[-1]
    #print(pos)
        
    if (pos <= 10):
        Ucolors = []
        for a in range (0,len(msNode[useview])):
            Rnow = AimColors[-1][a][0]
            Rprv = AimColors[-2][a][0]
            Rdo = ((Rnow-Rprv)*(pos/10))+Rprv
    
            Gnow = AimColors[-1][a][1]
            Gprv = AimColors[-2][a][1]
            Gdo = ((Gnow-Gprv)*(pos/10))+Gprv
    
            Bnow = AimColors[-1][a][2]
            Bprv = AimColors[-2][a][2]
            Bdo = ((Bnow-Bprv)*(pos/10))+Bprv
            
            Ucolors.append([Rdo,Gdo,Bdo])
    else:
        Ucolors = AimColors[-1]
        
    Rpos = len(ult_t)-Rot_t[-1]
    if (np.abs(AC[1]-EX)>RotThres) and (Rpos>10):
        Rot_t.append(len(ult_t))
        RotTyp.append(GetColors(AC[0],useview)[1])
        outfile.write('rotation\n')
    Rpos = len(ult_t)-Rot_t[-1]
    if Rpos < 10 and (Type=='hypercube'):
        if Type=='hypercube':
            allbool = False
        else:
            
            allbool = True
        if RotTyp[-1]==0:
            Rotate(np.pi/20,'x',useview,doall=allbool)
        if RotTyp[-1]==1:
            Rotate(-np.pi/20,'x',useview,doall=allbool)
        if RotTyp[-1]==2:
            Rotate(np.pi/20,'y',useview,doall=allbool)
        if RotTyp[-1]==3:
            Rotate(-np.pi/20,'y',useview,doall=allbool)
        if RotTyp[-1]==4:
            Rotate(np.pi/20,'z',useview,doall=allbool)
        if RotTyp[-1]==5:
            Rotate(-np.pi/20,'z',useview,doall=allbool)
        if Rpos==9 and Type=='hypercube':
            SnapInt(useview)
    if Rpos < 10 and Type=='AEM':
        if 0<=RotTyp[-1]<=2:
            RotateAEM(np.pi/30,useview)
        else:
            RotateAEM(np.pi/-30,useview)

    
    if Type =='nye' and 0<=timetodest<=60:
        Drop(useview)
        
    NowXT = (int(now_p*1000)-DayStarted)/3600000
    ult_t.append(NowXT)
    NodeCt=0
    
    #print(useview,Type,np.shape(Ucolors))
    
    for a in range (0,len(mShapeC[useview])):
        if mNode[useview][a]==1:
            red = Ucolors[NodeCt][0]/(256**2)
            green = Ucolors[NodeCt][1]/(256**2)
            blue = Ucolors[NodeCt][2]/(256**2)
            NodeCt += 1
            reds.append(red)
            greens.append(green)
            blues.append(blue)
            if Type=='quad':
                if a<4:
                    mkr = '|'
                else:
                    mkr = '_'
                ax1.scatter(mShapeC[useview][a][0],mShapeC[useview][a][1],mShapeC[useview][a][2],color=[red,green,blue],edgecolors=None,s=DotSize*2,marker=mkr)
            else:
                ax1.scatter(mShapeC[useview][a][0],mShapeC[useview][a][1],mShapeC[useview][a][2],color=[red,green,blue],edgecolors=None,s=DotSize,marker=Default_Marker)
    for a in range (0,len(mShapeC[useview])):
        if mNode[useview][a]==0:
            red = np.average(reds,weights=mDist[useview][a])
            green = np.average(greens,weights=mDist[useview][a])
            blue = np.average(blues,weights=mDist[useview][a])
            ax1.scatter(mShapeC[useview][a][0],mShapeC[useview][a][1],mShapeC[useview][a][2],color=[red,green,blue],edgecolors=None,s=DotSize,marker=Default_Marker)
            
            
    M = len(AimColors)-(2*len(viewlong))
    if pos <= 10:
        Nt = (len(ult_t)-(10*M)+(10-pos))-11
    else:
        Nt = (len(ult_t)-(10*M))-11
        
    R = len(RotTyp)
    if Rpos <= 10:
        NtR = (len(ult_t)-(10*R)+(10-Rpos))-11
    else:
        NtR = (len(ult_t)-(10*R))-11
    
    Mplt.append(M - (Pmod_Color*Nt))
    Mstd.append(((Nt*Pmod_Color*(1-Pmod_Color))**0.5)*1.65)
    
    Rplt.append(R - (Pmod_Rot*NtR))
    Rstd.append(((NtR*Pmod_Rot*(1-Pmod_Rot))**0.5)*1.65)
            
            
    plt.suptitle('%02d:%02d:%02d.%s%s UTC      |      T+ %02d:%02d:%02d'%(hrOfD,mnOfD,scOfD,microf,t_symbol,hrRun,mnRun,scRun),color=[np.average(reds),np.average(greens),np.average(blues)],size=wordsize)
    if Type == 'AEM':
        ax1.text(0,0,0,"%s"%(Bird),ha='center',va='center',color=[np.average(reds),np.average(greens),np.average(blues)],size=wordsize)
    if Type == 'quad':
        ax1.text(3,3,0,"%s"%(Bird),ha='center',va='center',color=[np.average(reds),np.average(greens),np.average(blues)],size=wordsize)
      
        
        
        
    ax1.grid(False)
    ax1.set_axis_off()
    if Type=='nye':
        ax1.plot(pollX,pollY,pollZ,color='white')
        ax1.set_xlim3d(-3.5,3.5)
        ax1.set_ylim3d(-3.5,3.5)
        ax1.set_zlim3d(-6.5,0.5)
        hoursleft = int(timetodest/3600)
        minleft = int(timetodest/60)%60
        secleft = int(timetodest%60)
        #plt.suptitle('%02d:%02d:%02d'%(hoursleft,minleft,secleft),size=70)
        Rotate(np.pi/20,'x',useview,doall=True)
        
    
    
    


            
    QBsums.append(AC[1])
    axQB.append(np.sum(QBsums)-(len(ult_t)*NEDspeed*8*0.5))
    for a in range(0,len(Xsums)):
        ax1y[a].append(np.sum(Xsums[a])-(len(ult_t)*NEDspeed*8*0.5))
        #print(a,(np.sum(Xsums[a])-(len(ult_t)*NEDspeed*8*0.5)))
    ax1s.append(((len(ult_t)*NEDspeed*8*0.25)**0.5)*1.96)
    ax1sN.append(((len(ult_t)*NEDspeed*8*0.25)**0.5)*-1.96)
    
    if zoomsto[0]==1:
        if TurboUse==True:
            ax2.plot(ult_t,ax1y[0],color='red',linewidth='1',label='Turbo')
            for a in range (1,len(ax1y)):
                ax2.plot(ult_t,ax1y[a],color='lightgray',linewidth='1')
        else:
            for a in range (0,len(ax1y)-1):
                ax2.plot(ult_t,ax1y[a],color='lightgray',linewidth='1')
        ax2.plot(ult_t,axQB,color='magenta',linewidth='1',label='Qbyte')
        ax2.plot(ult_t,ax1s,color='aqua',linestyle='--')
        ax2.plot(ult_t,ax1sN,color='aqua',linestyle='--')      
        ax3.plot(ult_t,Mplt,color='aqua',label='color change')
        ax3.plot(ult_t,Mstd,color='aqua',linestyle='--')
        ax3.plot(ult_t,Rplt,color='red',label='rotation')
        ax3.plot(ult_t,Rstd,color='red',linestyle='--')
        
        for a in range (0,len(riprise)):
            if StartXT<=riprise[a]<=NowXT:
                ax2.axvline(x=riprise[a],color='lightblue')
                ax3.axvline(x=riprise[a],color='lightblue')
        for a in range (0,len(ripset)):
            if StartXT<=ripset[a]<=NowXT:
                ax2.axvline(x=ripset[a],color='pink')
                ax3.axvline(x=ripset[a],color='pink')


    else:
                
        
        
        if TurboUse==True:
            ax2.plot(ult_t[-60:],np.array(ax1y[0][-60:])-ax1y[0][-60],color='red',linewidth='1',label='Turbo')
            for a in range (1,len(ax1y)):
                ax2.plot(ult_t[-60:],np.array(ax1y[a][-60:])-ax1y[a][-60],color='lightgray',linewidth='1')
        else:
            for a in range (0,len(ax1y)-1):
                ax2.plot(ult_t[-60:],np.array(ax1y[a][-60:])-ax1y[a][-60],color='lightgray',linewidth='1')
        ax2.plot(ult_t[-60:],np.array(axQB[-60:])-axQB[-60],color='magenta',linewidth='1',label='Qbyte')
        ax2.plot(ult_t[-60:],ax1s_zoom,color='aqua',linestyle='--')
        ax2.plot(ult_t[-60:],ax1sN_zoom,color='aqua',linestyle='--')      
        ax3.plot(ult_t[-60:],np.array(Mplt[-60:])-Mplt[-60],color='aqua',label='color change')
        ax3.plot(ult_t[-60:],Mstd_zoom,color='aqua',linestyle='--')
        ax3.plot(ult_t[-60:],np.array(Rplt[-60:])-Rplt[-60],color='red',label='rotation')
        ax3.plot(ult_t[-60:],Rstd_zoom,color='red',linestyle='--')

    
    
    ax4.plot(MIt,MI)
    ax4.set_yscale('log')
    ax4t.plot(MIt,CumP,color='red')
    ax4t.set_ylim([0,1])
    
    ax2.legend(loc=2)
    ax3.legend(loc=2)
    
    ax2.set_ylabel('raw deviations')
    ax3.set_ylabel('events')
    ax4.set_ylabel('Color Coherence 1/p (L) cum p (R)')

    
    if Type == 'pyramid':
        ax1.plot(BaseX,BaseY,BaseZ,color='white')
        ax1.plot(Beam1x,Beam1y,Beam1z,color='white')
        ax1.plot(Beam2x,Beam2y,Beam2z,color='white')
        
    
        
                
ani = animation.FuncAnimation(fig, animate, interval=1000)

plt.show()
