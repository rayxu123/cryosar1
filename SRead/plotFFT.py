#!/bin/python3
# Python 3.6 or greater
'''
Ray Xu
Jan 2023
cryosar1/SRead/SRead.py
'''

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
from mpldatacursor import datacursor    # pip3: mpldatacursor as root


# function to plot FFT
# Input: data (list of numbers representing time domain data), fs (sampling frequency), showNow (boolean, set to false and call plt.show() later)
# Return: ENOB, SNDR, SFDR, freq (list), PSD (list)
def plotFFT(data, fs, plot=True, showNow=True, title="FFT"):
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
    fmax_mag = np.amax(wave)
    fmax_idx = np.argmax(wave)
    wave = wave/fmax_mag
    PSD = 20*np.log10(wave)
    # specify numbins: number of bins +/- around the fundamental tone to count as signal bins
    numbins = 1
    sig_low_idx = max(0, fmax_idx-numbins)
    sig_high_idx = min(len(freq)-1, fmax_idx+numbins)
    # Calculate SFDR from PSD, in dB
    SFDR = -max(np.amax(PSD[0:sig_low_idx], initial=-np.inf), np.amax(PSD[sig_high_idx+1:len(PSD)], initial=-np.inf))
    # Calculate SNDR
    signal = wave[sig_low_idx:sig_high_idx+1]
    everythingelse_low = wave[0:sig_low_idx+1]
    everythingelse_high = wave[sig_high_idx:len(wave)]
    signal_power = np.sum(np.power(signal,2))
    everythingelse_low_power = np.sum(np.power(everythingelse_low,2))
    everythingelse_high_power = np.sum(np.power(everythingelse_high,2))
    SNDR = signal_power/(everythingelse_low_power + everythingelse_high_power)  # linear ratio
    SNDR = 10*np.log10(SNDR)            # dB scale
    ENOB = (SNDR-1.76)/6.02

    #print(SNDR)



    #print(SFDR)

    #print(freq)
    #print(PSD)


    if plot:
        fig_FFT, axs_FFT = plt.subplots(1,1,tight_layout=True)
        lines = axs_FFT.plot(freq, PSD, marker='o')
        axs_FFT.axhline(y=-SFDR, color="blue", linestyle='dashed')
        axs_FFT.title.set_text(title)
        axs_FFT.set_xlabel("Frequency [Hz]")
        axs_FFT.set_ylabel("PSD [dBc]")
        axs_FFT.set_xlim(0, np.amax(freq))
        axs_FFT.set_ylim(20*(np.floor(np.amin(PSD)/20)), 0)
        # Annotate
        if fmax_idx > len(freq)/2:
            axs_FFT.text(freq[int(np.floor(sig_low_idx-0.1*data_len))], -SFDR+5, "SFDR = "+"{:.1f}".format(SFDR)+" dBc\nSNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits", horizontalalignment='right')
        else:
            axs_FFT.text(freq[int(np.floor(sig_high_idx+0.1*data_len))], -SFDR+5, "SFDR = "+"{:.1f}".format(SFDR)+" dBc\nSNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits", horizontalalignment='left')

        datacursor(lines)
        if showNow: plt.show() 
    


    
