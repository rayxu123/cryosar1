#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
June 2026
cryosar1/DC/measV3_sineTwoTone_vs_amp.py

Does two-tone measurement using two AWGs.  Sweeps across amplitude for AWG1, AWG2, and combined (with power matching)

Make sure DIP switches are set to MAN, RAIL setting!


'''

import time, sys, subprocess, os
import numpy as np
import argparse
# Import shared folder
sys.path.insert(0, '../shared')
import hp33220a_visa
import datetime
from bitstring import BitArray
import csv
# Import SRead folder
sys.path.insert(0, '../SRead')
import fpga, calibration, plotFFT
from plotFFT import plotFFT
from plotFFT_TwoTone import plotFFT_TwoTone
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
import logger
import pandas as pd




if __name__ == "__main__":   
    # Some constants
    n1dB = np.power(10, -1/20)
    n3dB = np.power(10, -3/20)
    n6dB = np.power(10, -6/20)
    
    # Turn off interactive plotting.  Want to save FFT plots but not show them. 
    plt.ioff()
    
    # Input arguments
    parser = argparse.ArgumentParser(description='Two-tone sine measurement.')
    parser.add_argument('-n', '--name', dest='name', action='store', default="", help="Test name.  For metadata only.")
    parser.add_argument('-t', dest='setTemp', action='store', default=300, help="Set temperature, in kelvin.  For metadata only.")
    parser.add_argument('-d', dest='debug', action='store_true', default=False, help="Verbose output/debug output.")
    parser.add_argument('--npri1', dest='AWGnpri1', action='store', default='3733', type=float, help="AWG prime number of cycles to set frequency.  Freq=(npri/32768)*sampling rate.")
    parser.add_argument('--npri2', dest='AWGnpri2', action='store', default='3571', type=float, help="AWG prime number of cycles to set frequency.  Freq=(npri/32768)*sampling rate.")
    parser.add_argument('--amp', dest='AWGamp_initial', action='store', default='5', help="AWG amplitude in Vpp that is approximately -1dBFS.  The actual amplitude is fine tuned automatically.")
    parser.add_argument('--numpts', dest='numpts', action='store', default=64, type=int, help="Number of linearly space amplitude points.  (Defualt: 50)")
    args = parser.parse_args()
    
    # Init readout 
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    # Init AWG 
    awgFreq1 = (fpga.SER_RATE/fpga.SER_WIDTH)*args.AWGnpri1/fpga.FIFO_MAXDEPTH
    awgFreq2 = (fpga.SER_RATE/fpga.SER_WIDTH)*args.AWGnpri2/fpga.FIFO_MAXDEPTH
    awg1 = hp33220a_visa.hp33220a_visa(addr='USB0::0x0957::0x0407::MY44012694::INSTR')
    awg2 = hp33220a_visa.hp33220a_visa(addr='USB0::0x0957::0x0407::MY44012701::INSTR')
    awg1.initSine(awgFreq1, args.AWGamp_initial)
    awg2.initSine(awgFreq2, args.AWGamp_initial)
    awg1.setOutput(False)
    awg2.setOutput(False)

    ## Create data directory
    start = datetime.datetime.now()
    start = start.strftime('%Y%m%d_T%H%M%S')
    run_dir = "./output/run_"+start+"_"+args.name+"_"+str(args.setTemp)+"K"
    os.makedirs(run_dir)
    
    

    
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
    time.sleep(1.0)
    
    
    # Uncomment here to apply play values
    '''
    cal.odac = "01110101"
    cal.weights = [0.00000000, 1827.58368240, 1046.86900287, 600.86907152, 343.39610009, 196.53617856, 113.93648582, 66.88147999, 37.93098637, 22.86048889, 13.10705566, 7.57003784, 5.00000000, 3.00000000, 2.00000000, 1.00000000]
    '''
    
    
    ## Calibrate once to get the fullscale 
    tty = sys.stdout
    # Temporairily redirect stdout
    sys.stdout = logger.logger(run_dir+"/calibration.log")
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
    cal_fs_LSB = np.sum(cal.weights)
        
    
    
    ## Make amplitude sweep list for single-tone sweep first
    awg_list = np.logspace(np.log10(0.01), np.log10(10), num=args.numpts, endpoint=True)
    # Round to nearest 1 mV
    awg_list = np.round(awg_list*1000)/1000
    awg_list = np.unique(awg_list)  # Remove duplicates otherwise folder names will collide
    # Sort descending
    awg_list.sort()
    awg_list = np.flip(awg_list)
    
    
    

    

    ## Sweep AWG1
    data1_subfolder_list = []
    data1_range_cal_list = []
    data1_rms_cal_list = []
    data1_unique_cal_list = []
    data1_ENOB_cal_list = []
    data1_SNDR_cal_list = []
    data1_SFDR_cal_list = []
    data1_SNR_cal_list = []
    data1_SDR_cal_list = []
    data1_range_odacZS_list = []
    data1_unique_odacZS_list = []
    data1_ENOB_odacZS_list = []
    data1_SNDR_odacZS_list = []
    data1_SFDR_odacZS_list = []
    data1_SNR_odacZS_list = []
    data1_SDR_odacZS_list = []
    data1_range_odacMS_list = []
    data1_unique_odacMS_list = []
    data1_ENOB_odacMS_list = []
    data1_SNDR_odacMS_list = []
    data1_SFDR_odacMS_list = []
    data1_SNR_odacMS_list = []
    data1_SDR_odacMS_list = []
    data1_range_odacFS_list = []
    data1_unique_odacFS_list = []
    data1_ENOB_odacFS_list = []
    data1_SNDR_odacFS_list = []
    data1_SFDR_odacFS_list = []
    data1_SNR_odacFS_list = []
    data1_SDR_odacFS_list = []
    for awgAmp in awg_list:
        # Status printing 
        print(" ======== ======== ")
        print("Setting AWG1: AWGAMP={:f} in range [{:f}, {:f}]".format(awgAmp, np.amin(awg_list), np.amax(awg_list)))
        # Create raw data directory 
        rawdata_awgamp = "AWG1_AWGAMP{:05d}".format(int(awgAmp*1000))
        os.makedirs(run_dir+"/"+rawdata_awgamp, exist_ok=True)
        data1_subfolder_list.append(rawdata_awgamp)
        
        # Set AWG amp  
        awg1.initSine(awgFreq2, awgAmp)
        awg1.setOutput(True)
        # Let signals settle
        time.sleep(1.5)
        
        # Take data, calibrated ODAC
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
        
        # Datapoint statistics, calibrated ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_cal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data1_range_cal_list.append(datacal_range)
        data1_rms_cal_list.append(np.std(data))
        data1_unique_cal_list.append(datacal_unique)
        data1_ENOB_cal_list.append(datacal_ENOB)
        data1_SNDR_cal_list.append(datacal_SNDR)
        data1_SFDR_cal_list.append(datacal_SFDR)
        data1_SNR_cal_list.append(datacal_SNR)
        data1_SDR_cal_list.append(datacal_SDR)
        
        # Save raw data, calibrated ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_cal.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_cal_r2.txt", datar2)
        
        
        
        
        # Take data, zero ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"00000000",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, zero ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_odacZS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data1_range_odacZS_list.append(datacal_range)
        data1_unique_odacZS_list.append(datacal_unique)
        data1_ENOB_odacZS_list.append(datacal_ENOB)
        data1_SNDR_odacZS_list.append(datacal_SNDR)
        data1_SFDR_odacZS_list.append(datacal_SFDR)
        data1_SNR_odacZS_list.append(datacal_SNR)
        data1_SDR_odacZS_list.append(datacal_SDR)
        
        # Save raw data, zero ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacZS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacZS_r2.txt", datar2)
        
        
        # Take data, mid-scale ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"10000000",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, mid-scale ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_odacMS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data1_range_odacMS_list.append(datacal_range)
        data1_unique_odacMS_list.append(datacal_unique)
        data1_ENOB_odacMS_list.append(datacal_ENOB)
        data1_SNDR_odacMS_list.append(datacal_SNDR)
        data1_SFDR_odacMS_list.append(datacal_SFDR)
        data1_SNR_odacMS_list.append(datacal_SNR)
        data1_SDR_odacMS_list.append(datacal_SDR)
        
        # Save raw data, mid-scale ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacMS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacMS_r2.txt", datar2)
        
        
        # Take data, full-scale ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"11111111",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, full-scale ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_odacFS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data1_range_odacFS_list.append(datacal_range)
        data1_unique_odacFS_list.append(datacal_unique)
        data1_ENOB_odacFS_list.append(datacal_ENOB)
        data1_SNDR_odacFS_list.append(datacal_SNDR)
        data1_SFDR_odacFS_list.append(datacal_SFDR)
        data1_SNR_odacFS_list.append(datacal_SNR)
        data1_SDR_odacFS_list.append(datacal_SDR)
        
        # Save raw data, full-scale ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacFS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacFS_r2.txt", datar2)
    
    # Save aggregate data for AWG2 sweep
    data = {
        'awgAmp': awg_list,
        'subfolder': data1_subfolder_list,
        'data_range_cal': data1_range_cal_list,
        'data_rms_cal': data1_rms_cal_list,
        'data_unique_cal': data1_unique_cal_list,
        'data_ENOB_cal': data1_ENOB_cal_list,
        'data_SNDR_cal': data1_SNDR_cal_list,
        'data_SFDR_cal': data1_SFDR_cal_list,
        'data_SNR_cal': data1_SNR_cal_list,
        'data_SDR_cal': data1_SDR_cal_list,
        'data_range_odacZS': data1_range_odacZS_list,
        'data_unique_odacZS': data1_unique_odacZS_list,
        'data_ENOB_odacZS': data1_ENOB_odacZS_list,
        'data_SNDR_odacZS': data1_SNDR_odacZS_list,
        'data_SFDR_odacZS': data1_SFDR_odacZS_list,
        'data_SNR_odacZS': data1_SNR_odacZS_list,
        'data_SDR_odacZS': data1_SDR_odacZS_list,
        'data_range_odacMS': data1_range_odacMS_list,
        'data_unique_odacMS': data1_unique_odacMS_list,
        'data_ENOB_odacMS': data1_ENOB_odacMS_list,
        'data_SNDR_odacMS': data1_SNDR_odacMS_list,
        'data_SFDR_odacMS': data1_SFDR_odacMS_list,
        'data_SNR_odacMS': data1_SNR_odacMS_list,
        'data_SDR_odacMS': data1_SDR_odacMS_list,
        'data_range_odacFS': data1_range_odacFS_list,
        'data_unique_odacFS': data1_unique_odacFS_list,
        'data_ENOB_odacFS': data1_ENOB_odacFS_list,
        'data_SNDR_odacFS': data1_SNDR_odacFS_list,
        'data_SFDR_odacFS': data1_SFDR_odacFS_list,
        'data_SNR_odacFS': data1_SNR_odacFS_list,
        'data_SDR_odacFS': data1_SDR_odacFS_list
    }
    df = pd.DataFrame.from_dict(data)
    df.to_csv(run_dir+"/sweep_AWG1.csv")    
    # Do not open plots, release memory
    plt.close('all')
    
    
    ## Cleanup
    awg1.setOutput(False)
    awg2.setOutput(False)

    ## Sweep AWG2
    data2_subfolder_list = []
    data2_range_cal_list = []
    data2_rms_cal_list = []
    data2_unique_cal_list = []
    data2_ENOB_cal_list = []
    data2_SNDR_cal_list = []
    data2_SFDR_cal_list = []
    data2_SNR_cal_list = []
    data2_SDR_cal_list = []
    data2_range_odacZS_list = []
    data2_unique_odacZS_list = []
    data2_ENOB_odacZS_list = []
    data2_SNDR_odacZS_list = []
    data2_SFDR_odacZS_list = []
    data2_SNR_odacZS_list = []
    data2_SDR_odacZS_list = []
    data2_range_odacMS_list = []
    data2_unique_odacMS_list = []
    data2_ENOB_odacMS_list = []
    data2_SNDR_odacMS_list = []
    data2_SFDR_odacMS_list = []
    data2_SNR_odacMS_list = []
    data2_SDR_odacMS_list = []
    data2_range_odacFS_list = []
    data2_unique_odacFS_list = []
    data2_ENOB_odacFS_list = []
    data2_SNDR_odacFS_list = []
    data2_SFDR_odacFS_list = []
    data2_SNR_odacFS_list = []
    data2_SDR_odacFS_list = []
    for awgAmp in awg_list:
        # Status printing 
        print(" ======== ======== ")
        print("Setting AWG2: AWGAMP={:f} in range [{:f}, {:f}]".format(awgAmp, np.amin(awg_list), np.amax(awg_list)))
        # Create raw data directory 
        rawdata_awgamp = "AWG2_AWGAMP{:05d}".format(int(awgAmp*1000))
        os.makedirs(run_dir+"/"+rawdata_awgamp, exist_ok=True)
        data2_subfolder_list.append(rawdata_awgamp)
        
        # Set AWG amp  
        awg2.initSine(awgFreq2, awgAmp)
        awg2.setOutput(True)
        # Let signals settle
        time.sleep(1.5)
        
        # Take data, calibrated ODAC
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
        
        # Datapoint statistics, calibrated ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_cal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data2_range_cal_list.append(datacal_range)
        data2_rms_cal_list.append(np.std(data))
        data2_unique_cal_list.append(datacal_unique)
        data2_ENOB_cal_list.append(datacal_ENOB)
        data2_SNDR_cal_list.append(datacal_SNDR)
        data2_SFDR_cal_list.append(datacal_SFDR)
        data2_SNR_cal_list.append(datacal_SNR)
        data2_SDR_cal_list.append(datacal_SDR)
        
        # Save raw data, calibrated ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_cal.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_cal_r2.txt", datar2)
        
        
        
        # Take data, zero ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"00000000",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, zero ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_odacZS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data2_range_odacZS_list.append(datacal_range)
        data2_unique_odacZS_list.append(datacal_unique)
        data2_ENOB_odacZS_list.append(datacal_ENOB)
        data2_SNDR_odacZS_list.append(datacal_SNDR)
        data2_SFDR_odacZS_list.append(datacal_SFDR)
        data2_SNR_odacZS_list.append(datacal_SNR)
        data2_SDR_odacZS_list.append(datacal_SDR)
        
        # Save raw data, zero ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacZS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacZS_r2.txt", datar2)
        
        
        # Take data, mid-scale ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"10000000",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, mid-scale ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_odacMS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data2_range_odacMS_list.append(datacal_range)
        data2_unique_odacMS_list.append(datacal_unique)
        data2_ENOB_odacMS_list.append(datacal_ENOB)
        data2_SNDR_odacMS_list.append(datacal_SNDR)
        data2_SFDR_odacMS_list.append(datacal_SFDR)
        data2_SNR_odacMS_list.append(datacal_SNR)
        data2_SDR_odacMS_list.append(datacal_SDR)
        
        # Save raw data, mid-scale ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacMS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacMS_r2.txt", datar2)
        
        
        # Take data, full-scale ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"11111111",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, full-scale ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=run_dir+"/"+rawdata_awgamp+"/data_odacFS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        data2_range_odacFS_list.append(datacal_range)
        data2_unique_odacFS_list.append(datacal_unique)
        data2_ENOB_odacFS_list.append(datacal_ENOB)
        data2_SNDR_odacFS_list.append(datacal_SNDR)
        data2_SFDR_odacFS_list.append(datacal_SFDR)
        data2_SNR_odacFS_list.append(datacal_SNR)
        data2_SDR_odacFS_list.append(datacal_SDR)
        
        # Save raw data, full-scale ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacFS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacFS_r2.txt", datar2)
    
    # Save aggregate data for AWG2 sweep
    data = {
        'awgAmp': awg_list,
        'subfolder': data2_subfolder_list,
        'data_range_cal': data2_range_cal_list,
        'data_rms_cal': data2_rms_cal_list,
        'data_unique_cal': data2_unique_cal_list,
        'data_ENOB_cal': data2_ENOB_cal_list,
        'data_SNDR_cal': data2_SNDR_cal_list,
        'data_SFDR_cal': data2_SFDR_cal_list,
        'data_SNR_cal': data2_SNR_cal_list,
        'data_SDR_cal': data2_SDR_cal_list,
        'data_range_odacZS': data2_range_odacZS_list,
        'data_unique_odacZS': data2_unique_odacZS_list,
        'data_ENOB_odacZS': data2_ENOB_odacZS_list,
        'data_SNDR_odacZS': data2_SNDR_odacZS_list,
        'data_SFDR_odacZS': data2_SFDR_odacZS_list,
        'data_SNR_odacZS': data2_SNR_odacZS_list,
        'data_SDR_odacZS': data2_SDR_odacZS_list,
        'data_range_odacMS': data2_range_odacMS_list,
        'data_unique_odacMS': data2_unique_odacMS_list,
        'data_ENOB_odacMS': data2_ENOB_odacMS_list,
        'data_SNDR_odacMS': data2_SNDR_odacMS_list,
        'data_SFDR_odacMS': data2_SFDR_odacMS_list,
        'data_SNR_odacMS': data2_SNR_odacMS_list,
        'data_SDR_odacMS': data2_SDR_odacMS_list,
        'data_range_odacFS': data2_range_odacFS_list,
        'data_unique_odacFS': data2_unique_odacFS_list,
        'data_ENOB_odacFS': data2_ENOB_odacFS_list,
        'data_SNDR_odacFS': data2_SNDR_odacFS_list,
        'data_SFDR_odacFS': data2_SFDR_odacFS_list,
        'data_SNR_odacFS': data2_SNR_odacFS_list,
        'data_SDR_odacFS': data2_SDR_odacFS_list
    }
    df = pd.DataFrame.from_dict(data)
    df.to_csv(run_dir+"/sweep_AWG2.csv")    
    # Do not open plots, release memory
    plt.close('all')
    
    
    # Calculate scaling ratios for AWG1 and AWG2 for two-tone measurement
    p1 = np.polyfit(np.array(data1_rms_cal_list)*2*np.sqrt(2), awg_list, 1)   # slope is in Vpp/code range
    p2 = np.polyfit(np.array(data2_rms_cal_list)*2*np.sqrt(2), awg_list, 1)
    awg1_slope = p1[0]
    awg2_slope = p2[0]
    awg1_ratio = awg1_slope/(awg1_slope+awg2_slope)
    awg2_ratio = awg2_slope/(awg1_slope+awg2_slope)
    awg1_FS = awg1_slope*awg1_ratio*(cal_fs_LSB)*0.95
    awg2_FS = awg2_slope*awg2_ratio*(cal_fs_LSB)*0.95
    
    
    
    awg1.initSine(awgFreq1, awg1_FS)
    awg2.initSine(awgFreq2, awg2_FS)
    
    
    
    ## Make amplitude sweep list for two-tone sweep first
    awg_list = np.logspace(np.log10(cal_fs_LSB*0.001), np.log10(cal_fs_LSB), num=args.numpts, endpoint=True)
    np.concatenate([awg_list, [cal_fs_LSB*n1dB]])
    np.concatenate([awg_list, [cal_fs_LSB*n3dB]])
    np.concatenate([awg_list, [cal_fs_LSB*n6dB]])
    awg1_list = awg_list*awg1_slope*awg1_ratio
    awg2_list = awg_list*awg2_slope*awg2_ratio
    # This must be atomic operation
    awg1_list_new = awg1_list[(awg1_list >= 0.01) & (awg2_list >= 0.01)]
    awg2_list_new = awg2_list[(awg1_list >= 0.01) & (awg2_list >= 0.01)]
    awg1_list = awg1_list_new
    awg2_list = awg2_list_new
    awg1_list.sort()
    awg2_list.sort()
    # Round to nearest 1 mV
    awg1_list = np.round(awg1_list*1000)/1000
    awg2_list = np.round(awg2_list*1000)/1000
    # Remove duplicates otherwise folder names will collide.  This must be an atomic operation
    mask_list = [True]*len(awg1_list)
    for n in range(1,len(awg1_list)):
        if awg1_list[n] == awg1_list[n-1]: mask_list[n] = False
        if awg2_list[n] == awg2_list[n-1]: mask_list[n] = False
    awg1_list = awg1_list[mask_list]
    awg2_list = awg2_list[mask_list]
    # Sort descending
    awg1_list = np.flip(awg1_list)
    awg2_list = np.flip(awg2_list)


    ## Two tone sweep
    dataTT_subfolder_list = []
    dataTT_range_cal_list = []
    dataTT_rms_cal_list = []
    dataTT_unique_cal_list = []
    dataTT_ENOB_cal_list = []
    dataTT_SNDR_cal_list = []
    dataTT_SFDR_cal_list = []
    dataTT_SNR_cal_list = []
    dataTT_SDR_cal_list = []
    dataTT_range_odacZS_list = []
    dataTT_unique_odacZS_list = []
    dataTT_ENOB_odacZS_list = []
    dataTT_SNDR_odacZS_list = []
    dataTT_SFDR_odacZS_list = []
    dataTT_SNR_odacZS_list = []
    dataTT_SDR_odacZS_list = []
    dataTT_range_odacMS_list = []
    dataTT_unique_odacMS_list = []
    dataTT_ENOB_odacMS_list = []
    dataTT_SNDR_odacMS_list = []
    dataTT_SFDR_odacMS_list = []
    dataTT_SNR_odacMS_list = []
    dataTT_SDR_odacMS_list = []
    dataTT_range_odacFS_list = []
    dataTT_unique_odacFS_list = []
    dataTT_ENOB_odacFS_list = []
    dataTT_SNDR_odacFS_list = []
    dataTT_SFDR_odacFS_list = []
    dataTT_SNR_odacFS_list = []
    dataTT_SDR_odacFS_list = []
    for awg1Amp,awg2Amp in zip(awg1_list,awg2_list):
        # Status printing 
        print(" ======== ======== ")
        print("Setting AWG1 (TT): AWGAMP={:f} in range [{:f}, {:f}]".format(awg1Amp, np.amin(awg1_list), np.amax(awg1_list)))
        # Create raw data directory 
        rawdata_awgamp = "AWGTT_AWGAMP{:05d}".format(int(awg1Amp*1000))
        os.makedirs(run_dir+"/"+rawdata_awgamp, exist_ok=True)
        dataTT_subfolder_list.append(rawdata_awgamp)
        
        # Set AWG amp  
        awg1.initSine(awgFreq1, awg1Amp)
        awg1.setOutput(True)
        awg2.initSine(awgFreq2, awg2Amp)
        awg2.setOutput(True)
        # Let signals settle
        time.sleep(1.5)
        
        # Take data, calibrated ODAC
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
        
        # Datapoint statistics, calibrated ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT_TwoTone(data, fpga.SER_RATE/8, plot=True, showNow=False, annotate=False, title="Calibrated, 12b levels", numbins=3, numharm=3, save=run_dir+"/"+rawdata_awgamp+"/data_cal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        dataTT_range_cal_list.append(datacal_range)
        dataTT_rms_cal_list.append(np.std(data))
        dataTT_unique_cal_list.append(datacal_unique)
        dataTT_ENOB_cal_list.append(datacal_ENOB)
        dataTT_SNDR_cal_list.append(datacal_SNDR)
        dataTT_SFDR_cal_list.append(datacal_SFDR)
        dataTT_SNR_cal_list.append(datacal_SNR)
        dataTT_SDR_cal_list.append(datacal_SDR)
        
        # Save raw data, calibrated ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_cal.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_cal_r2.txt", datar2)
        
        
        
        # Take data, zero ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"00000000",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, zero ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT_TwoTone(data, fpga.SER_RATE/8, plot=True, showNow=False, annotate=False, title="Calibrated, 12b levels", numbins=3, numharm=3, save=run_dir+"/"+rawdata_awgamp+"/data_odacZS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        dataTT_range_odacZS_list.append(datacal_range)
        dataTT_unique_odacZS_list.append(datacal_unique)
        dataTT_ENOB_odacZS_list.append(datacal_ENOB)
        dataTT_SNDR_odacZS_list.append(datacal_SNDR)
        dataTT_SFDR_odacZS_list.append(datacal_SFDR)
        dataTT_SNR_odacZS_list.append(datacal_SNR)
        dataTT_SDR_odacZS_list.append(datacal_SDR)
        
        # Save raw data, zero ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacZS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacZS_r2.txt", datar2)
        
        
        # Take data, mid-scale ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"10000000",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, mid-scale ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT_TwoTone(data, fpga.SER_RATE/8, plot=True, showNow=False, annotate=False, title="Calibrated, 12b levels", numbins=3, numharm=3, save=run_dir+"/"+rawdata_awgamp+"/data_odacMS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        dataTT_range_odacMS_list.append(datacal_range)
        dataTT_unique_odacMS_list.append(datacal_unique)
        dataTT_ENOB_odacMS_list.append(datacal_ENOB)
        dataTT_SNDR_odacMS_list.append(datacal_SNDR)
        dataTT_SFDR_odacMS_list.append(datacal_SFDR)
        dataTT_SNR_odacMS_list.append(datacal_SNR)
        dataTT_SDR_odacMS_list.append(datacal_SDR)
        
        # Save raw data, mid-scale ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacMS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacMS_r2.txt", datar2)
        
        
        # Take data, full-scale ODAC
        try:
            subprocess.run([sys.executable, 
                "./../SControl/SControl.py", 
                "-b",
                "-o", "ODAC_CODE,"+"11111111",
                "-f", "./../SControl/config/CryoSAR1.cfg"], check=True)
        except Exception as e:
            sys.exit(e)
        data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=1)
        if valid is False: print("WARNING: non-valid sample encountered!")
        
        # Datapoint statistics, full-scale ODAC
        datacal_unique = len(np.unique(np.round(data)))
        datacal_range = np.ptp(data)
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT_TwoTone(data, fpga.SER_RATE/8, plot=True, showNow=False, annotate=False, title="Calibrated, 12b levels", numbins=3, numharm=3, save=run_dir+"/"+rawdata_awgamp+"/data_odacFS.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Do not open plots, release memory
        plt.close('all')
        dataTT_range_odacFS_list.append(datacal_range)
        dataTT_unique_odacFS_list.append(datacal_unique)
        dataTT_ENOB_odacFS_list.append(datacal_ENOB)
        dataTT_SNDR_odacFS_list.append(datacal_SNDR)
        dataTT_SFDR_odacFS_list.append(datacal_SFDR)
        dataTT_SNR_odacFS_list.append(datacal_SNR)
        dataTT_SDR_odacFS_list.append(datacal_SDR)
        
        # Save raw data, full-scale ODAC
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacFS.txt", data)
        np.savetxt(run_dir+"/"+rawdata_awgamp+"/data_odacFS_r2.txt", datar2)
    
    # Save aggregate data for AWGTT sweep
    data = {
        'awg1Amp': awg1_list,
        'awg2Amp': awg2_list,
        'subfolder': dataTT_subfolder_list,
        'data_range_cal': dataTT_range_cal_list,
        'data_rms_cal': dataTT_rms_cal_list,
        'data_unique_cal': dataTT_unique_cal_list,
        'data_ENOB_cal': dataTT_ENOB_cal_list,
        'data_SNDR_cal': dataTT_SNDR_cal_list,
        'data_SFDR_cal': dataTT_SFDR_cal_list,
        'data_SNR_cal': dataTT_SNR_cal_list,
        'data_SDR_cal': dataTT_SDR_cal_list,
        'data_range_odacZS': dataTT_range_odacZS_list,
        'data_unique_odacZS': dataTT_unique_odacZS_list,
        'data_ENOB_odacZS': dataTT_ENOB_odacZS_list,
        'data_SNDR_odacZS': dataTT_SNDR_odacZS_list,
        'data_SFDR_odacZS': dataTT_SFDR_odacZS_list,
        'data_SNR_odacZS': dataTT_SNR_odacZS_list,
        'data_SDR_odacZS': dataTT_SDR_odacZS_list,
        'data_range_odacMS': dataTT_range_odacMS_list,
        'data_unique_odacMS': dataTT_unique_odacMS_list,
        'data_ENOB_odacMS': dataTT_ENOB_odacMS_list,
        'data_SNDR_odacMS': dataTT_SNDR_odacMS_list,
        'data_SFDR_odacMS': dataTT_SFDR_odacMS_list,
        'data_SNR_odacMS': dataTT_SNR_odacMS_list,
        'data_SDR_odacMS': dataTT_SDR_odacMS_list,
        'data_range_odacFS': dataTT_range_odacFS_list,
        'data_unique_odacFS': dataTT_unique_odacFS_list,
        'data_ENOB_odacFS': dataTT_ENOB_odacFS_list,
        'data_SNDR_odacFS': dataTT_SNDR_odacFS_list,
        'data_SFDR_odacFS': dataTT_SFDR_odacFS_list,
        'data_SNR_odacFS': dataTT_SNR_odacFS_list,
        'data_SDR_odacFS': dataTT_SDR_odacFS_list
    }
    df = pd.DataFrame.from_dict(data)
    df.to_csv(run_dir+"/sweep_AWGTT.csv")    
    # Do not open plots, release memory
    plt.close('all')
    
    


    ## Cleanup
    awg1.setOutput(False)
    awg2.setOutput(False)
    awg1.close()
    awg2.close()
    fpga.close()






