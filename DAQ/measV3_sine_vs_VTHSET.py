#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Sept 2024
cryosar1/DC/measV3_sine_vs_VTHSET.py

Sweeps across VTHSET values and measures sine wave performance

Make sure DIP switches are set to FDBK, DAC setting!

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


if __name__ == "__main__":
    print("REMINDER: Make sure DIP switches are set to FDBK, DAC setting!")
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
    parser.add_argument('-t', dest='setTemp', action='store', default=25, help="Set temperature, in celsius.  For metadata only.")
    parser.add_argument('-s', dest='sweep', action='store', default="4,4,512", help="VTHSET sweep in start,step,stop inclusive.  Units in DAC setting out of 1024 (1.2V). Defualt: 4,4,512")
    parser.add_argument('-d', dest='debug', action='store_true', default=False, help="Verbose output/debug output.")
    parser.add_argument('--npri', dest='AWGnpri', action='store', default='1823', type=float, help="AWG prime number of cycles to set frequency.  Freq=(npri/32768)*sampling rate.")
    parser.add_argument('--amp', dest='AWGamp', action='store', default='1.79', help="AWG amplitude in Vpp that is approximately -1dBFS.  The actual amplitude is fine tuned automatically.")
    parser.add_argument('-i', dest='enableINLDNL', action='store_true', default=False, help="Enable INL/DNL data taking.  Really only useful for 1MHz.  Default=False")
    parser.add_argument('--imult', dest='imult', action='store', default=32, type=int, help="Number of 32k sample multiples for INL/DNL.  Default: 32")
    args = parser.parse_args()
    
    # Init readout 
    fpga = fpga.fpga()
    cal = calibration.calibration(fpga)
    
    # Init AWG 
    awgFreq = (fpga.SER_RATE/fpga.SER_WIDTH)*args.AWGnpri/fpga.FIFO_MAXDEPTH
    awg = hp33220a_visa.hp33220a_visa(addr='USB0::0x0957::0x0407::MY44012694::INSTR')
    awg.initSine(awgFreq, args.AWGamp)

    # Parse sweep and initialize dataframe
    userCommentsDict = {"setTemp": args.setTemp,
                        "sweep": args.sweep,
                        "npri": args.AWGnpri,
                        "AWGamp_initial": args.AWGamp,
                        "INLDNL": args.enableINLDNL,
                        "INLDNL_mult": args.imult,
                        "userComments": ""}
    pw = pandasWriter.pandasWriter(userComments=userCommentsDict, compress=False, csvFilePrefix=os.path.splitext(os.path.basename(__file__))[0])
    startDAC = int(args.sweep.split(",")[0])
    stepDAC = int(args.sweep.split(",")[1])
    stopDAC = int(args.sweep.split(",")[2])
    sweepList = np.arange(startDAC, stopDAC+stepDAC, stepDAC)
    sweepList = np.flip(sweepList)  # Start with highest VTH setting (VBN and VBP most near rails)
    np.append(sweepList, 512)   # Manually add VTHSET=0.6V to imitate no adaptive feedback
    # Create data directory
    rawdata_dir = "./output/"+os.path.splitext(os.path.basename(pw.csvFilepath()))[0]+"_rawdata"
    os.makedirs(rawdata_dir)
    
    

    
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

    

    # Sweep VTHSET
    for vthset in sweepList:
        vthset_int = int(vthset)
        vthset_bin = BitArray(uint=vthset_int, length=10).bin
        # Status printing 
        print(" ======== ======== ")
        print("Setting VTHSET={:d} in range [{:d}, {:d}, {:d}]".format(vthset_int, int(startDAC), int(stepDAC), int(stopDAC)))
        # Create raw data directory 
        rawdata_vth = rawdata_dir+"./VTHSET{:04d}".format(vthset_int)
        os.makedirs(rawdata_vth)
        
        

        ## Set VTHSET        
        try:
            subprocess.run([sys.executable,
                "./../SControl/SControl_DAC.py", 
                "-o", "DAC5A_data,"+vthset_bin,
                "-b",
                "-f", "./../SControl/config/CryoSAR1_DAC.cfg"])
        except Exception as e:
            sys.exit(e)

        ## Let signals settle
        time.sleep(0.1)

        ## Calibrate 
        
        awg.setOutput(False)
        cal.calibrate_ODAC_using_weights_v2(verbose=args.debug)
        cal_odac_int = BitArray(bin=cal.odac).uint
        cal.calibrate_weights(verbose=args.debug)
        cal_weights_list = cal.weights.copy()
        print("Calibrated ODAC: \""+str(cal.odac)+"\"")
        print("Calibrated weight:")
        print("["+', '.join([f'{item:.8f}' for item in cal.weights])+"]")
        cal_fs_LSB = np.sum(cal.weights)
        
        '''
        # Debugging only 
        cal.odac = "01110101"
        cal.weights = [0.00000000, 1869.56270071, 1070.89532451, 614.97527326, 351.08871370, 201.17846070, 116.51853248, 68.28396822, 38.86395719, 23.22273254, 13.34252930, 7.67655945, 5.00000000, 3.00000000, 2.00000000, 1.00000000]
        cal_fs_LSB = np.sum(cal.weights)
        '''
        
        
        ## Take calibrated data to fine tune AWG amplitude 
        # Apply data taking configuration + ODAC calibration
        awg.setOutput(True)
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
        awg_FS = awg.getAmp()*(cal_fs_LSB/sine_ptp)
        
        
        ## Take calibrated data for measurement at -1dBFS 
        # Round down to the nearest 0.01Vpp
        AWG_n1dBM = np.floor(awg_FS*n1dB*100)/100
        awg.initSine(awgFreq, AWG_n1dBM)
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
        datacal_ENOB, datacal_SNDR, datacal_SFDR, datacal_SNR, datacal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="Calibrated, 12b levels", numbins=3, numharm=11, save=rawdata_vth+"/data_cal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        #if args.debug is True:
        if True:
            print("Calibrated ENOB: "+str(datacal_ENOB)) 
            print("Calibrated SNDR: "+str(datacal_SNDR)) 
            print("Calibrated SFDR: "+str(datacal_SFDR)) 
        # Save raw data
        np.savetxt(rawdata_vth+"/data_cal.txt", data)
        
        
        ## INL DNL data, if enabled (MUST do immediately after taking clibrated data to preserve DUT configuration)
        if args.enableINLDNL is True:
            data, valid, datar2 = fpga.takeData("data", bipolar=False, printBinary=False, weighting=cal.weights, mult=args.imult)
            if True:
                print("Number of unique codes: "+str(len(np.unique(data))))
                print("Code coverage [%]: "+str(100*len(np.unique(data))/np.ptp(data)))
                print("Calibrated stddev [LSB]: "+str(np.std(data)))
                print("Calibrated range [LSB]: "+str(np.ptp(data)))
                print("Calibrated FS (-1dBFS) [LSB]: "+str(np.sum(cal.weights))+" ("+str(0.9*np.sum(cal.weights))+")")
            if (np.ptp(data) > (np.sum(cal.weights)*0.9)):
                print("WARNING: Exceeding 90% of FS")
            np.savetxt(rawdata_vth+"/data_cal_inldnl.txt.gz", data)
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
            plt.savefig(rawdata_vth+"/inldnl.png", dpi=900, pad_inches=0)
            np.savetxt(rawdata_vth+"/dnl.txt", dnl)
            np.savetxt(rawdata_vth+"/inl.txt", inl)
            # Get quick statistics
            DNL_min = np.amin(dnl)
            DNL_max = np.amax(dnl)
            INL_min = np.amin(inl)
            INL_max = np.amax(inl)
            print("DNL min/max: {:f}/{:f}".format(DNL_min, DNL_max))
            print("INL min/max: {:f}/{:f}".format(INL_min, INL_max))
        else:
            DNL_min = 0
            DNL_max = 0
            INL_min = 0
            INL_max = 0
        
        
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
        datauncal_ENOB, datauncal_SNDR, datauncal_SFDR, datauncal_SNR, datauncal_SDR, _, _, _, _, _ = plotFFT(data, fpga.SER_RATE/8, plot=True, showNow=False, title="UnCalibrated, 12b levels", numbins=3, numharm=11, save=rawdata_vth+"/data_uncal.png")    # Uncomment this for 12b code levels, but floating point arithmetic
        # Save raw data
        np.savetxt(rawdata_vth+"/data_uncal.txt", data)
        
        
        
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
                    "VTHSET_DAC": vthset_int,
                    "sensorA": sensorA,
                    "relpath": rawdata_vth,
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
                    "DNL_min": DNL_min,
                    "DNL_max": DNL_max,
                    "INL_min": INL_min,
                    "INL_max": INL_max,
                    "cal_FS": cal_fs_LSB,
                    "cal_n1dB": cal_fs_LSB*n1dB,
                    "AWG_n1dB": AWG_n1dBM,
                    "AWG_FS": awg_FS,
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

    print("\n")
    pw.writeCSV()











