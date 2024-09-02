#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Sept 2024
cryosar1/DC/measV3_sine_vs_amp.py

Sweeps across AWG amplitude and measures sine wave performance

Make sure DIP switches are set to MAN, RAIL setting!

Have CryoCon running in the background to poll every second!
'''

import time, sys, subprocess, os
import numpy as np
import argparse
# Import shared folder
sys.path.insert(0, '../shared')
import hp33220a_visa
import pandasWriter
from bitstring import BitArray
import csv
# Import SRead folder
sys.path.insert(0, '../SRead')
import fpga, calibration, plotFFT
from plotFFT import plotFFT
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
import logger


if __name__ == "__main__":
    print("REMINDER: Make sure DIP switches are set to MAN, RAIL setting!")
    print("REMINDER: Have CryoCon running in the background to poll every second!")
    
    # Some constants
    n1dB = np.power(10, -1/20)
    n2dB = np.power(10, -2/20)
    n3dB = np.power(10, -3/20)
    n4dB = np.power(10, -4/20)
    n5dB = np.power(10, -5/20)
    n6dB = np.power(10, -6/20)
    
    # Turn off interactive plotting.  Want to save FFT plots but not show them. 
    plt.ioff()
    
    # Input arguments
    parser = argparse.ArgumentParser(description='Sweeps across VTHSET values and measures biases.')
    parser.add_argument('-t', dest='setTemp', action='store', default=300, help="Set temperature, in kelvin.  For metadata only.")
    parser.add_argument('-d', dest='debug', action='store_true', default=False, help="Verbose output/debug output.")
    parser.add_argument('--npri', dest='AWGnpri', action='store', default='1823', type=float, help="AWG prime number of cycles to set frequency.  Freq=(npri/32768)*sampling rate.")
    parser.add_argument('--amp', dest='AWGamp_initial', action='store', default='1.79', help="AWG amplitude in Vpp that is approximately -1dBFS.  The actual amplitude is fine tuned automatically.")
    parser.add_argument('--numpts', dest='numpts', action='store', default=64, type=int, help="Number of linearly space amplitude points.  (Defualt: 256)")
    parser.add_argument('-i', dest='enableINLDNL', action='store_true', default=False, help="Enable INL/DNL data taking.  Really only useful for 1MHz.  Default=False")
    parser.add_argument('--imult', dest='imult', action='store', default=32, type=int, help="Number of 32k sample multiples for INL/DNL.  Default: 32")
    args = parser.parse_args()
    
    # Init readout 
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    # Init AWG 
    awgFreq = (fpga.SER_RATE/fpga.SER_WIDTH)*args.AWGnpri/fpga.FIFO_MAXDEPTH
    awg = hp33220a_visa.hp33220a_visa(addr='USB0::0x0957::0x0407::MY44012694::INSTR')
    awg.initSine(awgFreq, args.AWGamp_initial)

    # Initialize dataframe
    userCommentsDict = {"setTemp": args.setTemp,
                        "npri": args.AWGnpri,
                        "AWGamp_initial": args.AWGamp_initial,
                        "INLDNL": args.enableINLDNL,
                        "INLDNL_mult": args.imult,
                        "numpts": args.numpts,
                        "userComments": ""}
    pw = pandasWriter.pandasWriter(userComments=userCommentsDict, compress=False, csvFilePrefix=os.path.splitext(os.path.basename(__file__))[0])
    # Create data directory
    rawdata_dir = "./output/"+os.path.splitext(os.path.basename(pw.csvFilepath()))[0]+"_rawdata"
    os.makedirs(rawdata_dir)
    
    

    
    # Initialize DUT
    awg.setOutput(False)
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
    time.sleep(1.0)
        
    ## Calibrate once to get the fullscale 
    sys.stdout = logger.logger(rawdata_dir+"./log.txt")
    cal.calibrate_ODAC_using_weights_v2()
    cal_odac_int = BitArray(bin=cal.odac).uint
    cal.calibrate_weights()
    cal_weights_list = cal.weights.copy()
    print("==== ====")
    print("Calibrated ODAC: \""+str(cal.odac)+"\"")
    print("Calibrated weight:")
    print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
    cal_fs_LSB = np.sum(cal.weights)
    
    ## Take calibrated data to fine tune AWG amplitude 
    # Apply data taking configuration + ODAC calibration
    awg.setOutput(True)
    time.sleep(1.0)
    print("Take calibrated data to determine FS.")
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
    if valid is False: print("WARNING: non-valid sample encountered!")
    sine_ptp = np.ptp(data)
    awg_fs_VPP = awg.getAmp()*(cal_fs_LSB/sine_ptp)
    print("AWG FS VPP: "+str(awg_fs_VPP))
    
    ## Make amplitude sweep list 
    awg_list = np.linspace(0.01, awg_fs_VPP, num=args.numpts, endpoint=True)
    # Append specific points, e.g. -1dBFS, -2dBFS, etc.
    awg_list = np.append(awg_list, awg_fs_VPP*n1dB)
    awg_list = np.append(awg_list, awg_fs_VPP*n2dB)
    awg_list = np.append(awg_list, awg_fs_VPP*n3dB)
    awg_list = np.append(awg_list, awg_fs_VPP*n4dB)
    awg_list = np.append(awg_list, awg_fs_VPP*n5dB)
    awg_list = np.append(awg_list, awg_fs_VPP*n6dB)
    # Round to nearest 1 mV
    awg_list = np.round(awg_list*1000)/1000
    awg_list = np.unique(awg_list)  # Remove duplicates otherwise folder names will collide
    # Sort descending
    awg_list.sort()
    awg_list = np.flip(awg_list)
    
    
    ## Take pedestal, uncalibrated 
    awg.setOutput(False)
    time.sleep(1.0)
    print("Take pedestal data, uncalibrated")
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.CAL_ODAC_DEFAULT,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.CAL_WEIGHTS_DEFAULT.copy(), mult=4)
    if valid is False: print("WARNING: non-valid sample encountered!")
    # Save raw data
    np.savetxt(rawdata_dir+"./baseline_uncal.txt", data)
    np.savetxt(rawdata_dir+"./baseline_uncal_r2.txt", datar2)
    
    ## Take pedestal, calibrated 
    awg.setOutput(False)
    time.sleep(1.0)
    print("Take pedestal data, calibrated")
    try:
        subprocess.run([sys.executable, 
            "./../SControl/SControl.py", 
            "-b",
            "-o", "ODAC_CODE,"+cal.odac,
            "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
    except Exception as e:
        sys.exit(e)
    data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=4)
    if valid is False: print("WARNING: non-valid sample encountered!")
    # Save raw data
    np.savetxt(rawdata_dir+"./baseline_cal.txt", data)
    np.savetxt(rawdata_dir+"./baseline_cal_r2.txt", datar2)
    
    ## Take INL/DNL at -1dBFS 
    ## INL DNL data, if enabled (MUST do immediately after taking calibrated data to preserve DUT configuration)
    if args.enableINLDNL is True:
        print("Taking INL DNL")
        awg.initSine(awgFreq, (np.floor(awg_fs_VPP*n1dB*100)/100)-0.005)    # Round to lowest 10mV and minus 5mV
        awg.setOutput(True)
        time.sleep(1.0)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=args.imult)
        if True:
            print("Number of unique codes: "+str(len(np.unique(data))))
            print("Code coverage [%]: "+str(100*len(np.unique(data))/np.ptp(data)))
            print("Calibrated stddev [LSB]: "+str(np.std(data)))
            print("Calibrated range [LSB]: "+str(np.ptp(data)))
            print("Calibrated FS (-1dBFS) [LSB]: "+str(cal_fs_LSB)+" ("+str(n1dB*cal_fs_LSB)+")")
        if (np.ptp(data) > (n1dB*cal_fs_LSB)):
            print("WARNING: Exceeding 90% of FS")
        np.savetxt(rawdata_dir+"/data_cal_inldnl.txt.gz", data)
        np.savetxt(rawdata_dir+"/data_cal_r2_inldnl.txt.gz", datar2)
        # Calculate DNL then INL
        # Histogram
        N = np.log2(np.max(data)-np.min(data))
        hist, bin_edges = np.histogram(data, bins = np.arange(np.min(data), np.max(data), 1), density=True)
        bin_edges = bin_edges[:-1]
        # A different way of calculating INL, using best fit method from sine wave
        # https://gitlab.cern.ch/jgonski/colutaanalysis/-/blob/dev_kiryeong/cv4_analysis/plotting/plots_slow_sine.py
        # https://www3.advantest.com/documents/11348/27fd03db-3c5d-49e7-afb9-e0bcb6861cee
        A = (np.max(data)-np.min(data))/2
        if args.debug is True: print(np.sum(hist))
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
        plt.savefig(rawdata_dir+"/inldnl.png", dpi=900, pad_inches=0)
        np.savetxt(rawdata_dir+"/dnl.txt", dnl)
        np.savetxt(rawdata_dir+"/inl.txt", inl)
        np.savetxt(rawdata_dir+"/binedges.txt", bin_edges)
        # Get quick statistics
        DNL_min = np.amin(dnl)
        DNL_max = np.amax(dnl)
        INL_min = np.amin(inl)
        INL_max = np.amax(inl)
        print("DNL min/max: {:f}/{:f}".format(DNL_min, DNL_max))
        print("INL min/max: {:f}/{:f}".format(INL_min, INL_max))

    

    # Sweep AWG amplitude 
    for awgAmp in awg_list:
        # Status printing 
        print(" ======== ======== ")
        print("Setting AWGAMP={:f} in range [{:f}, {:f}]".format(awgAmp, np.amin(awg_list), np.amax(awg_list)))
        # Create raw data directory 
        rawdata_awgamp = rawdata_dir+"./AWGAMP{:04d}".format(int(awgAmp*1000))
        os.makedirs(rawdata_awgamp)
        
        
        ## Set AWG amp  
        awg.initSine(awgFreq, awgAmp)
        awg.setOutput(True)
        # Let signals settle
        time.sleep(0.3)
        
        
        

        ## Take UNcalibrated data for measurement at -1dBFS 
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+cal.CAL_ODAC_DEFAULT,
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.CAL_WEIGHTS_DEFAULT.copy(), mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        datauncal_unique = len(np.unique(np.round(data)))
        datauncal_range = np.ptp(data)
        '''
        if args.debug is True:
            print("UnCalibrated Number of unique codes: "+str(datauncal_unique))
            print("UnCalibrated stddev [LSB]: "+str(np.std(data)))
            print("UnCalibrated range [LSB]: "+str(datauncal_range))
            print("UnCalibrated FS (-1dBFS) [LSB]: "+str(cal_fs_LSB)+" ("+str(n1dB*cal_fs_LSB)+")")
        if (datacal_range > (n1dB*cal_fs_LSB)):
            print("WARNING: Exceeding 90% of FS")
        '''
        datauncal_ENOB, datauncal_SNDR, datauncal_SFDR, datauncal_SNR, datauncal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="UnCalibrated, 12b levels", numbins=3, numharm=11, save=rawdata_awgamp+"/data_uncal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Save raw data
        np.savetxt(rawdata_awgamp+"/data_uncal.txt", data)
        np.savetxt(rawdata_awgamp+"/data_uncal_r2.txt", datar2)
        
        ## Take calibrated data 
        print("Take calibrated data @ AWG amplitude sweep")
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+cal.odac,
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        #if args.debug is True:
        if True:
            print("Calibrated number of unique codes: "+str(datacal_unique))
            print("Calibrated stddev [LSB]: "+str(np.std(data)))
            print("Calibrated range [LSB]: "+str(datacal_range))
            print("Calibrated FS (-1dBFS) [LSB]: "+str(cal_fs_LSB)+" ("+str(n1dB*cal_fs_LSB)+")")
        if (datacal_range > (n1dB*cal_fs_LSB)):
            print("WARNING: Exceeding 90% of FS")
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=rawdata_awgamp+"/data_cal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        #if args.debug is True:
        if True:
            print("Calibrated ENOB: "+str(datacal_ENOB)) 
            print("Calibrated SNDR: "+str(datacal_SNDR)) 
            print("Calibrated SFDR: "+str(datacal_SFDR)) 
        # Save raw data
        np.savetxt(rawdata_awgamp+"/data_cal.txt", data)
        np.savetxt(rawdata_awgamp+"/data_cal_r2.txt", datar2)
        
        # Read AD7888
        try:
            subprocess.run([sys.executable,
                "./../SControl/SControl_DAC.py", 
                "-r",
                "-q"])
        except Exception as e:
            sys.exit(e)
        with open("./output/adc.csv") as csv_file:
            reader = csv.reader(csv_file)
            ad7888_data = dict(reader)
        
        # Read sensor A last temperature file
        with open("./../CryoCon/sensorA_last", "r") as f:
            while True:
                try:
                    sensorA = float(f.read())
                except Exception as e:
                    continue # File may be being written
                else:
                    break
        
        # Combine data dictionaries
        dataDict = {
                    "AWGamp": awgAmp,
                    "sensorA": sensorA,
                    "relpath": rawdata_awgamp,
                    "datacal_unique": datacal_unique,
                    "datacal_range": datacal_range,
                    "datacal_ENOB": datacal_ENOB,
                    "datacal_SNDR": datacal_SNDR, 
                    "datacal_SFDR": datacal_SFDR, 
                    "datacal_SNR": datacal_SNR, 
                    "datacal_SDR": datacal_SDR,
                    "datauncal_unique": datauncal_unique,
                    "datauncal_range": datauncal_range,
                    "datauncal_ENOB": datauncal_ENOB,
                    "datauncal_SNDR": datauncal_SNDR, 
                    "datauncal_SFDR": datauncal_SFDR, 
                    "datauncal_SNR": datauncal_SNR, 
                    "datauncal_SDR": datauncal_SDR,         
                    "cal_FS": cal_fs_LSB,
                    "AWG_FS": awg_fs_VPP,
                    "cal_odac": cal_odac_int,
                    "cal_W15": cal_weights_list[1],
                    "cal_W14": cal_weights_list[2],
                    "cal_W13": cal_weights_list[3],
                    "cal_W12": cal_weights_list[4],
                    "cal_W11": cal_weights_list[5],
                    "cal_W10": cal_weights_list[6],
                    "cal_W9": cal_weights_list[7],
                    "cal_W8": cal_weights_list[8],
                    "cal_W7": cal_weights_list[9],
                    "cal_W6": cal_weights_list[10],
                    "cal_W5": cal_weights_list[11],
                    "cal_W4": cal_weights_list[12],
                    "cal_W3": cal_weights_list[13],
                    "cal_W2": cal_weights_list[14],
                    "cal_W1": cal_weights_list[15]
                    }
        dataDict = {**dataDict, **ad7888_data}
        pw.appendData(dataDict)
        # Do not open plots, release memory
        plt.close('all')

    print("\n")
    pw.writeCSV()











