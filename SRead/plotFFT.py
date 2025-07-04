#!/bin/python3
# Python 3.6 or greater
# MatPlotLib 3.6.3
'''
Ray Xu
March 2023
plotFFT
'''

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
#from mpldatacursor import datacursor    # pip3: mpldatacursor as root


# function to plot FFT
# Input: data (list of numbers representing time domain data), fs (sampling frequency in Hz), showNow (boolean, set to false and call plt.show() later), save (path to png output, otherwise None to skip saving)
# Return: ENOB, SNDR, SFDR, SNR, SDR, freq (list), PSD (list), fig, axs
def plotFFT(data, fs, plot=True, showNow=True, title=None, save=None, numharm=9, numbins=0, fmax_idx=None, drawSFDRLine=True):
    dco = np.mean(data)
    data_len = len(data)  
    # Remove DC offset
    data = [i-dco for i in data]
    # Calculate PSD
    wave = np.fft.fft(data)
    freq = np.fft.fftfreq(data_len, 1/fs)
    # Scaling with respect to data length, get single-sided spectrum, normalize against fundamental, and calculate PSD in log10
    # Specify dcbins: number of bins to count as DC energy (suggested: 1)
    dcbins = 1
    wave = np.abs(wave/data_len)
    wave = wave[dcbins:int(np.floor(data_len/2))]*2
    freq = freq[dcbins:int(np.floor(data_len/2))]
    if fmax_idx is None:
        fmax_idx = np.argmax(wave)
    # If fmax_idx is forced, calculations will use that bin id as the main signal tone
    fmax_mag = wave[fmax_idx]
    wave = wave/fmax_mag
    PSD = 20*np.log10(wave)
    # specify numbins: number of bins +/- around the fundamental tone to count as signal bins
    #numbins = 1
    sig_low_idx = max(0, fmax_idx-numbins)
    sig_high_idx = min(len(freq)-1, fmax_idx+numbins)
    # Calculate SFDR from PSD, in dB
    # Compatability for older numpy
    #SFDR = -max(np.amax(PSD[0:sig_low_idx], initial=-np.inf), np.amax(PSD[sig_high_idx+1:len(PSD)], initial=-np.inf))
    if (len(PSD[0:sig_low_idx]) > 0) and (len(PSD[sig_high_idx+1:len(PSD)]) > 0):
        SFDR = -max(np.amax(PSD[0:sig_low_idx]), np.amax(PSD[sig_high_idx+1:len(PSD)]))
    elif (len(PSD[0:sig_low_idx]) == 0) and (len(PSD[sig_high_idx+1:len(PSD)]) > 0):
        SFDR = -max(0, np.amax(PSD[sig_high_idx+1:len(PSD)]))
    elif (len(PSD[0:sig_low_idx]) > 0) and (len(PSD[sig_high_idx+1:len(PSD)]) == 0):
        SFDR = -max(np.amax(PSD[0:sig_low_idx]), 0)
    # Calculate SNDR
    signal = wave[sig_low_idx:sig_high_idx+1]   # range [sig_low_idx, sig_high_idx]
    everythingelse_low = wave[0:sig_low_idx]    # range [0, sig_low_idx)
    everythingelse_high = wave[sig_high_idx+1:len(wave)]    # range (sig_high_idx, end]
    signal_power = np.sum(np.power(signal,2))
    everythingelse_low_power = np.sum(np.power(everythingelse_low,2))
    everythingelse_high_power = np.sum(np.power(everythingelse_high,2))
    everythingelse_power = everythingelse_low_power + everythingelse_high_power
    SNDR = signal_power/(everythingelse_power)  # linear ratio
    SNDR = 10*np.log10(SNDR)            # dB scale
    ENOB = (SNDR-1.76)/6.02

    # Compute harmonic locations
    # https://www.analog.com/en/design-notes/foldedfrequency-calculator.html
    # The expression listed in the webpage text may be wrong.  The implemented expression below uses what is in the spreadsheet which is linked on the webpage.
    #numharm = 9         # Number of tones to identify including the fundamental
    fnyquist = fs/2
    fund_freq = freq[fmax_idx]
    harm_freq = np.zeros(numharm-1)
    harm_freq_aliased = np.zeros(numharm-1)
    harm_idx = np.zeros(numharm-1)
    harm_power = 0
    for i in np.arange(numharm-1):    
        harm_freq[i] = fund_freq*(i+2)
        #print(str(harm_freq[i]))
        # Does harmonic fall in an even zone?
        if np.mod(np.floor(harm_freq[i]/fnyquist), 2) == 0:
            harm_freq_aliased[i] = np.mod(harm_freq[i], fnyquist)
        else:
            harm_freq_aliased[i] = fnyquist - np.mod(harm_freq[i], fnyquist)
        harm_idx[i] = np.where(freq == harm_freq_aliased[i])[0][0]
        harm_low_idx = int(max(0, harm_idx[i]-numbins))
        harm_high_idx = int(min(len(freq)-1, harm_idx[i]+numbins))
        harm_power = harm_power + np.sum(np.power(wave[harm_low_idx:harm_high_idx+1],2))
    SNR = signal_power/(everythingelse_power - harm_power)
    SNR = 10*np.log10(SNR)
    SDR = signal_power/(harm_power)
    SDR = 10*np.log10(SDR)
        
        
    # In case plot is disabled
    fig_FFT = None
    axs_FFT = None
    if plot:
        fig_FFT, axs_FFT = plt.subplots(1,1,tight_layout=True)
        lines = axs_FFT.plot(freq, PSD)
        if drawSFDRLine: axs_FFT.axhline(y=-SFDR, color="blue", linestyle='dashed')
        if title is not None: axs_FFT.title.set_text(title)
        axs_FFT.set_xlabel("Frequency [Hz]")
        axs_FFT.set_ylabel("PSD [dBc]")
        axs_FFT.set_xlim(0, np.amax(freq)+0.5*np.unique(np.diff(freq))) # Add one more frequency step to the right to make the last x tick show
        axs_FFT.set_ylim(20*(np.floor(np.amin(PSD)/20)), 0)
        axs_FFT.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
        # Annotate
        if fmax_idx > len(freq)/2:
            axs_FFT.text(freq[int(np.floor(sig_low_idx-0.15*data_len))], -50, "SNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits\nSFDR = "+"{:.1f}".format(SFDR)+" dBc\nSNR = "+"{:.1f}".format(SNR)+" dB\nSDR = "+"{:.1f}".format(SDR)+" dB", horizontalalignment='center', backgroundcolor='white', bbox=dict(ec='black', fc='white'))
        else:
            axs_FFT.text(freq[int(np.floor(sig_high_idx+0.15*data_len))], -50, "SNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits\nSFDR = "+"{:.1f}".format(SFDR)+" dBc\nSNR = "+"{:.1f}".format(SNR)+" dB\nSDR = "+"{:.1f}".format(SDR)+" dB", horizontalalignment='center', backgroundcolor='white', bbox=dict(ec='black', fc='white'))

        # Plot harmonics
        for i in np.arange(numharm-1):
            axs_FFT.plot(freq[int(harm_idx[int(i)])], PSD[int(harm_idx[int(i)])], marker="^", mec="red", mfc="red", mew=2)
            axs_FFT.text(freq[int(harm_idx[int(i)])], PSD[int(harm_idx[int(i)])]+5, str(i+2), fontweight='bold', color='red', horizontalalignment='center')

        #datacursor(lines)
        if showNow: plt.show() 

        if save is not None: plt.savefig(save)

    
    return ENOB, SNDR, SFDR, SNR, SDR, freq, PSD, fig_FFT, axs_FFT, fmax_idx


    
