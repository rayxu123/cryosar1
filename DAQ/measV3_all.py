#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
July 2025
cryosar1/DAQ/measV3_all.py

Performs data collection at a given set temperature.  
Data being taken:
 * temperature reading
 * DC operating points
 * calibration
 * pedestal
 * 1 MHz amplitude sweep
 * 1 MHz INL/DNL
 * 8 MHz amplitude sweep

Make sure DIP switches are set to MAN, RAIL setting.

Have CryoCon or TMon running in the background to poll every second!
'''

import time, sys, subprocess, os, csv, argparse, datetime, logger, copy
import numpy as np
import pandas as pd
from bitstring import BitArray
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
from matplotlib.ticker import AutoMinorLocator, MultipleLocator, LogLocator
# Import shared folder
sys.path.insert(0, '../shared')
import hp33220a_visa, pandasWriter
# Import SRead folder
sys.path.insert(0, '../SRead')
import fpga, calibration
from plotFFT import plotFFT


# Test: INL DNL
def inldnl(awgFS, dataDir):
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Set AWG to 95% FS
    awg.initSine(c.awg1MHz_freq, awgFS*0.95)
    awg.setOutput(True)
    # Let signals settle
    time.sleep(1.2)
    # Take data
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=args.mult)
    np.savetxt(dataDir+"/data_cal_inldnl.txt.gz", data)
    np.savetxt(dataDir+"/data_cal_r2_inldnl.txt.gz", datar2)
    # Calculate DNL then INL
    # Histogram
    N = np.log2(np.max(data)-np.min(data))
    hist, bin_edges = np.histogram(data, bins = np.arange(np.min(data), np.max(data), 1), density=True)
    bin_edges = bin_edges[:-1]
    # A different way of calculating INL, using best fit method from sine wave
    # https://gitlab.cern.ch/jgonski/colutaanalysis/-/blob/dev_kiryeong/cv4_analysis/plotting/plots_slow_sine.py
    # https://www3.advantest.com/documents/11348/27fd03db-3c5d-49e7-afb9-e0bcb6861cee
    A = (np.max(data)-np.min(data))/2
    print(np.sum(hist))
    M = np.sum(hist)   # This needs to equal unity
    sum_Hk = np.cumsum(hist)    # Cumulative distribution function
    # Back-calculate the probability distribution function to obtain the transition locations
    V_j = -A*np.cos((np.pi/M)*sum_Hk)
    # Calculate DNL
    dnl = np.diff(V_j) - 1
    # Perform best line of fit, for use in INL
    V_fit = np.poly1d(np.polyfit(bin_edges, V_j, 1))
    inl = V_j - V_fit(bin_edges)
    # Plot INL/DNL
    fig, (axs1, axs2) = plt.subplots(2,1,tight_layout=True, sharex=True)
    fig.set_size_inches(8, 8)
    axs1.plot(bin_edges[:-1], dnl)
    axs2.plot(bin_edges, inl)
    # Plot graphics
    axs1.grid(which='both')
    axs2.grid(which='both')
    axs1.set_ylabel(r"DNL [LSB]")
    axs2.set_ylabel(r"INL [LSB]")
    axs2.set_xlabel(r"Code")
    # Save
    plt.savefig(dataDir+"/inldnl.png", dpi=900, pad_inches=0)
    np.savetxt(dataDir+"/dnl.txt", dnl)
    np.savetxt(dataDir+"/inl.txt", inl)
    np.savetxt(dataDir+"/binedges.txt", bin_edges)
    # Get quick statistics
    DNL_min = np.amin(dnl)
    DNL_max = np.amax(dnl)
    INL_min = np.amin(inl)
    INL_max = np.amax(inl)
    print("DNL min/max: {:f}/{:f}".format(DNL_min, DNL_max))
    print("INL min/max: {:f}/{:f}".format(INL_min, INL_max))
    plt.show()
    
    

# Test: Sine amplitude sweep
# Returns the AWG FS for the given frequency
def sineSweep(freq, initAmp, dataDir):
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    
    # Find AWG FS
    awgFS = find_AWGFS(freq, initAmp)
    print("Found AWG FS: "+str(awgFS)+" Vpp")
    
    # Generate log spaced amplitude points
    awg_list = np.logspace(np.log2(0.01), np.log2(awgFS), num=args.numpts, endpoint=True, base=2)
    # Append specific points, e.g. -1dBFS, -2dBFS, etc.
    awg_list = np.append(awg_list, awgFS*c.n1dB)
    awg_list = np.append(awg_list, awgFS*c.n2dB)
    awg_list = np.append(awg_list, awgFS*c.n3dB)
    awg_list = np.append(awg_list, awgFS*c.n4dB)
    awg_list = np.append(awg_list, awgFS*c.n5dB)
    awg_list = np.append(awg_list, awgFS*c.n6dB)
    awg_list = np.append(awg_list, awgFS*c.n7dB)
    awg_list = np.append(awg_list, awgFS*c.n8dB)
    awg_list = np.append(awg_list, awgFS*c.n9dB)
    awg_list = np.append(awg_list, awgFS*c.n10dB)
    awg_list = np.append(awg_list, awgFS*c.n11dB)
    awg_list = np.append(awg_list, awgFS*c.n12dB)
    # Round to nearest 1 mV
    awg_list = np.round(awg_list*1000)/1000
    awg_list = np.unique(awg_list)  # Remove duplicates otherwise folder names will collide
    # Sort descending
    awg_list.sort()
    awg_list = np.flip(awg_list)
    
    # Sweep AWG amplitude 
    temperature_list = []
    data_subfolder_list = []
    data_range_list = []
    data_unique_list = []
    data_ENOB_list = []
    data_SNDR_list = []
    data_SFDR_list = []
    data_SNR_list = []
    data_SDR_list = []
    for awgAmp in awg_list:
        # Status printing 
        print(" ======== ======== ")
        print("Setting AWGAMP={:f} in range [{:f}, {:f}]".format(awgAmp, np.amin(awg_list), np.amax(awg_list)))
        # Create raw data directory 
        rawdata_awgamp = "AWGAMP{:04d}".format(int(awgAmp*1000))
        os.makedirs(dataDir+"/"+rawdata_awgamp, exist_ok=True)
        
        # Set AWG amp  
        awg.initSine(freq, awgAmp)
        awg.setOutput(True)
        # Let signals settle
        time.sleep(1.5)
        
        # Take data
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics
        datauncal_unique = len(np.unique(np.round(data)))
        datauncal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=dataDir+"/"+rawdata_awgamp+"/data_cal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        temperature_list.append(readTemp(args.tmon))
        data_range_list.append(datauncal_range)
        data_unique_list.append(datauncal_unique)
        data_ENOB_list.append(datacal_ENOB)
        data_SNDR_list.append(datacal_SNDR)
        data_SFDR_list.append(datacal_SFDR)
        data_SNR_list.append(datacal_SNR)
        data_SDR_list.append(datacal_SDR)
        data_subfolder_list.append(rawdata_awgamp)
        # Save raw data
        np.savetxt(dataDir+"/"+rawdata_awgamp+"/data_cal.txt", data)
        np.savetxt(dataDir+"/"+rawdata_awgamp+"/data_cal_r2.txt", datar2)
    # Save aggregate data
    data = {
        'awgAmp': awg_list,
        'subfolder': data_subfolder_list,
        'temperature': temperature_list,
        'data_range': data_range_list,
        'data_unique': data_unique_list,
        'data_ENOB': data_ENOB_list,
        'data_SNDR': data_SNDR_list,
        'data_SFDR': data_SFDR_list,
        'data_SNR': data_SNR_list,
        'data_SDR': data_SDR_list
    }
    df = pd.DataFrame.from_dict(data)
    df.to_csv(dataDir+"sweep.csv")    
    # Do not open plots, release memory
    plt.close('all')
    # Debug plots
    fig, axs = plt.subplots(1,1,tight_layout=True)
    axs.semilogx(data_range_list, data_SNDR_list, '-*', base=2)  # This property might be called 'base' or 'basex' depending on matplotlib version
    axs.xaxis.set_minor_locator(LogLocator(base=2, subs =[1.5]))
    axs.yaxis.set_major_locator(MultipleLocator(5))
    axs.yaxis.set_minor_locator(MultipleLocator(1))
    axs.set_xlabel("Code range [LSB]")
    axs.set_ylabel("SNDR [dB]")
    plt.grid(which='both', axis='both')
    idx = getidx(awg_list, awgFS*c.n1dB)
    print("At -1 dBFS:")
    print("Calibrated number of unique codes: "+str(data_unique_list[idx]))
    print("Calibrated range [LSB]: "+str(data_range_list[idx]))
    print("Calibrated FS (-1dBFS) [LSB]: "+str(np.sum(cal.weights))+" ("+str(c.n1dB*np.sum(cal.weights))+")")
    print("Calibrated ENOB: "+str(data_ENOB_list[idx])) 
    print("Calibrated SNDR: "+str(data_SNDR_list[idx])) 
    print("Calibrated SFDR: "+str(data_SFDR_list[idx])) 
    p = data_subfolder_list[idx]
    data = np.loadtxt(dataDir+"/"+p+"/data_cal.txt")
    plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=None)
    plt.show()
    return awgFS
    

# Find AWG voltage amplitude to reach ADC full-scale
# initAmp has to be below the actual full-scale and be linear
def find_AWGFS(initFreq, initAmp):
    awg.initSine(initFreq, initAmp)
    awg.setOutput(True)
    # Wait for signal to settle
    time.sleep(0.5)
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
    if valid is False: print("WARNING: non-valid sample encountered!")
    scalefactor = np.sum(cal.weights)/np.ptp(data)
    return scalefactor*initAmp
    

# Test: Take pedestal data
def takePedestal(datadir):
    print("Taking pedestal data.")
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    time.sleep(0.3)
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=args.mult)
    if valid is False: print("WARNING: non-valid sample encountered!")
    # Save raw data
    np.savetxt(datadir+"/baseline_cal.txt.gz", data)
    np.savetxt(datadir+"/baseline_cal_r2.txt.gz", datar2)
    # Debug printing
    data_rounded = np.round(data)
    data_unique = np.unique(data_rounded)
    data_stddev = np.std(data_rounded)
    print("Pedestal Values: "+str(data_unique))
    print("Pedestal Stddev: "+str(data_stddev))

# Test: calibration
def calibrate(datadir):
    tty = sys.stdout
    # Temporairily redirect stdout
    sys.stdout = logger.logger(datadir+"/calibration.log")
    cal.calibrate_ODAC_using_weights_v2()
    cal_odac_int = BitArray(bin=cal.odac).uint
    cal.calibrate_weights()
    cal_weights_list = cal.weights.copy()
    print("==== ====")
    print("Calibrated ODAC: \""+str(cal.odac)+"\"")
    print("Calibrated weight:")
    print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
    sys.stdout = tty
    # Load in calibrated ODAC
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    time.sleep(0.3)


# Test: Read DC
def readDC():
    # Baseline reading under default config
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-r",
            "-q",
            "--average=100"])
    except Exception as e:
        sys.exit(e)
    with open("./output/adc.csv") as csv_file:
        reader = csv.reader(csv_file)
        DC_baseline = dict(reader)
    # Read Ref buffer output
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg",
            "-o", "VREFP_EXT_EN,1",
            "-o", "VREFN_EXT_EN,1",
            "-o", "VCM_EXT_EN,1",
            "-o", "VREFP_VC_EN,0",
            "-o", "VREFN_VC_EN,0",
            "-o", "VCM_VC_EN,0"], check=True)
    except Exception as e:
        sys.exit(e) 
    time.sleep(0.3)
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-r",
            "-q",
            "--average=100"])
    except Exception as e:
        sys.exit(e)
    with open("./output/adc.csv") as csv_file:
        reader = csv.reader(csv_file)
        DC_extRB = dict(reader)
    # Read Ref buffer gate voltage output
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg",
            "-o", "VREFP_EXT_EN,0",
            "-o", "VREFN_EXT_EN,0",
            "-o", "VCM_EXT_EN,0",
            "-o", "VREFP_VC_EN,1",
            "-o", "VREFN_VC_EN,1",
            "-o", "VCM_VC_EN,1"], check=True)
    except Exception as e:
        sys.exit(e) 
    time.sleep(0.3)
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-r",
            "-q",
            "--average=100"])
    except Exception as e:
        sys.exit(e)
    with open("./output/adc.csv") as csv_file:
        reader = csv.reader(csv_file)
        DC_extVC = dict(reader)
    # Restore default config
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    # Merge relevant dicts
    DC = copy.deepcopy(DC_baseline)
    DC['VREFP_RB'] = copy.deepcopy(DC_extRB['VREFP_EXT'])
    DC['VREFN_RB'] = copy.deepcopy(DC_extRB['VREFN_EXT'])
    DC['VREFCM_RB'] = copy.deepcopy(DC_extRB['VREFCM_EXT'])
    DC['VREFP_VC'] = copy.deepcopy(DC_extVC['VREFP_EXT'])
    DC['VREFN_VC'] = copy.deepcopy(DC_extVC['VREFN_EXT'])
    DC['VREFCM_VC'] = copy.deepcopy(DC_extVC['VREFCM_EXT']) 
    # Print
    for k in DC:
        print(k+": {:.3f} V".format(2.5*(float(DC[k])/4096)))
    return DC


# Read temperature and return value
def readTemp(tmon):
    if tmon is True: fpath = "./../TMon/sensor_last"
    else: fpath = "./../CryoCon/sensorA_last"
    # Read sensor A or TMon last temperature file
    with open(fpath, "r") as f:
        while True:
            try:
                sensor = float(f.read())
            except Exception as e:
                continue # File may be being written
            else:
                break
    return sensor

# Wrapper for individual tests
def wrapper(inPrompt, outPrompt, retry, method, *args, **kwargs):
    print("=====")
    if inPrompt is not None:
        print(inPrompt)
        if input("Press [ENTER] to proceed or [q][ENTER] to quit.") == 'q': exit()
    output = method(*args, **kwargs)
    if outPrompt is not None: print(outPrompt)
    if retry is True:
        query = input("Press [ENTER] to proceed or [r][ENTER] to redo test or [q][ENTER] to quit.")
        if query == 'q': exit()
        if query == 'r': 
            output = wrapper(None, outPrompt, retry, method, *args, **kwargs)
    else:
        #if input("Press [ENTER] to proceed or [q][ENTER] to quit.") == 'q': exit()
        pass
    print("=====")
    return output
    
# Get index of closest value
# https://stackoverflow.com/questions/9706041/finding-index-of-an-item-closest-to-the-value-in-a-list-thats-not-entirely-sort
def getidx(l, v): return np.argmin(np.abs(np.array(l)-v))


    

class consts():
    f = fpga.fpga(noConnect=True)
    # Some constants
    n1dB = np.power(10, -1/20)
    n2dB = np.power(10, -2/20)
    n3dB = np.power(10, -3/20)
    n4dB = np.power(10, -4/20)
    n5dB = np.power(10, -5/20)
    n6dB = np.power(10, -6/20)
    n7dB = np.power(10, -7/20)
    n8dB = np.power(10, -8/20)
    n9dB = np.power(10, -9/20)
    n10dB = np.power(10, -10/20)
    n11dB = np.power(10, -11/20)
    n12dB = np.power(10, -12/20)
    awg1MHz_freq = (f.SER_RATE/f.SER_WIDTH)*1823/f.FIFO_MAXDEPTH
    awg1MHz_amp = 1.5
    awg8MHz_freq = (f.SER_RATE/f.SER_WIDTH)*14591/f.FIFO_MAXDEPTH
    awg8MHz_amp = 1.5
    

if __name__ == "__main__":
    c = consts()    

    print("REMINDER: Make sure DIP switches are set to MAN, RAIL setting!")
    print("REMINDER: Have CryoCon or TMon running in the background to poll every second!")
    
    
    
    # Turn off interactive plotting.  Want to save FFT plots but not show them. 
    plt.ioff()
    
    # Input arguments
    parser = argparse.ArgumentParser(description='Takes data for a set temperature.')
    parser.add_argument('-t', dest='setTemp', action='store', default=300, help="Set temperature, in kelvin.  For metadata only.")
    parser.add_argument('-n', dest='name', action='store', default='', help="Run name.")
    parser.add_argument('--tmon', dest='tmon', action='store_true', default=False, help="Read temperature from TMon application.  Default=False")
    parser.add_argument('--dc', dest='dc', action='store_true', default=False, help="Only do DC measurement.  Default=False")
    parser.add_argument('--numpts', dest='numpts', action='store', default=52, type=int, help="Number of linearly space amplitude points.  (Defualt: 52)")
    parser.add_argument('--mult', dest='mult', action='store', default=32, type=int, help="Number of 32k sample multiples for INL/DNL and pedestal.  Default: 32")
    args = parser.parse_args()
    
    # Create data directory
    start = datetime.datetime.now()
    start = start.strftime('%Y%m%d_T%H%M%S')
    run_dir = "./output/run_"+start+"_"+args.name+"_"+str(args.setTemp)+"K"
    os.makedirs(run_dir)

    # Init readout 
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    # Init AWG 
    #awg = hp33220a_visa.hp33220a_visa(addr='USB0::0x0957::0x0407::MY44012701::INSTR')
    awg = hp33220a_visa.hp33220a_visa(addr='USB0::0x0957::0x0407::MY44012694::INSTR')
    awg.initSine(c.awg1MHz_freq, c.awg1MHz_amp)
    awg.setOutput(False)
    
    # Initialize DUT
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-b",
            "-f", "./../SControl/config/CryoSAR1_DAC.cfg"])
    except Exception as e:
        sys.exit(e)
    try:
        subprocess.run([sys.executable,
            "./../SControl/SControl_DAC.py", 
            "-r",
            "-q"])
    except Exception as e:
        sys.exit(e)
    # Wait for signal to settle 
    time.sleep(0.3)
    
    # Test: DC and temperature reading
    DC = wrapper("DC Reading.  Connect input to 50 Ohm termination.", None, False, readDC)
    with open("./"+run_dir+"/DC.csv", "w") as f:
        writer = csv.writer(f)
        for key, value in DC.items():
            writer.writerow([key, value])
    temperature = str(readTemp(args.tmon))
    with open("./"+run_dir+"/temperature.csv", "w") as f: f.write(temperature)
    
    if args.dc is True: exit()
    
    # Test: calibration
    wrapper(None, None, False, calibrate, run_dir)
    with open("./"+run_dir+"/cal_weights", "w") as f: 
        wr = csv.writer(f)
        wr.writerow(cal.weights)
    with open("./"+run_dir+"/cal_odac", "w") as f: f.write(str(cal.odac))
    cal_FS_LSB = np.sum(cal.weights)
        
    # Test: take pedestal data, calibrated
    wrapper(None, None, False, takePedestal, run_dir)
    
    # Test: 1 MHz amplitude sweep
    awgFS = wrapper("Connect 1 MHz BPF.", None, True, sineSweep, c.awg1MHz_freq, c.awg1MHz_amp, run_dir+"/sinesweep_1MHz/")
    
    # Test: INL/DNL
    wrapper(None, None, True, inldnl, awgFS, run_dir)
    
    # Test: 8 MHz amplitude sweep
    awgFS = wrapper("Connect 8 MHz BPF.", None, True, sineSweep, c.awg8MHz_freq, c.awg8MHz_amp, run_dir+"/sinesweep_8MHz/")











