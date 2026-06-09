#!/bin/python3
# Python 3.6 or greater
# MatPlotLib 3.6.3
'''
Ray Xu
June 2026
plotFFT_TwoTone
'''

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt     # DNF: python3-matplotlib
#from mpldatacursor import datacursor    # pip3: mpldatacursor as root


# function to plot FFT
# Input: data (list of numbers representing time domain data), fs (sampling frequency in Hz), showNow (boolean, set to false and call plt.show() later), save (path to png output, otherwise None to skip saving)
# Return: ENOB, SNDR, SFDR, SNR, SDR, freq (list), PSD (list), fig, axs
def plotFFT_TwoTone(data, fs, plot=True, showNow=True, title=None, save=None, numharm=9, numbins=0, annotate=True, drawSFDRLine=True, annoIMD=True):
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
    wave = wave[0:int(np.floor(data_len/2))]*2
    freq = freq[0:int(np.floor(data_len/2))]
    #wave = wave[dcbins:int(np.floor(data_len/2))]*2
    #freq = freq[dcbins:int(np.floor(data_len/2))]

    f1_idx = np.flip(np.argsort(wave))[0]
    f2_idx = np.flip(np.argsort(wave))[1]
    
    fmax_mag = np.amax([wave[f1_idx], wave[f2_idx]])
    wave = wave/fmax_mag
    PSD = 20*np.log10(wave)
    # specify numbins: number of bins +/- around the fundamental tone to count as signal bins
    numbins = 1
    # Mask out fund tones
    fmask = [True]*len(freq)
    for i in range(len(freq)):
        if (i >= f1_idx-numbins) and (i <= f1_idx+numbins): fmask[i] = False
        if (i >= f2_idx-numbins) and (i <= f2_idx+numbins): fmask[i] = False
    # Mask out DC bins
    for i in range(dcbins):
        fmask[i] = False


    
    # Calculate SFDR
    SFDR = -np.amax(PSD[fmask])
    print(SFDR)
    
    
    # Calculate SNDR
    signal_mask = [not x for x in fmask]
    signal = wave[signal_mask]
    everythingelse = wave[fmask]
    signal_power = np.sum(np.power(signal,2))
    everythingelse_power = np.sum(np.power(everythingelse,2))
    SNDR = signal_power/(everythingelse_power)  # linear ratio
    SNDR = 10*np.log10(SNDR)            # dB scale
    ENOB = (SNDR-1.76)/6.02
    

    '''
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
    '''
    SNR = np.nan
    SDR = np.nan
    
    ## Compute harmonic and modulation products
    # Second order
    if numharm >= 2:
        hd2 = []
        hd2.append(f1_idx*2)
        hd2.append(f2_idx*2)
        hd2.append(np.abs(f2_idx-f1_idx))
        hd2.append(np.abs(f2_idx+f1_idx))
    if numharm >= 3:
        hd3 = []
        hd3.append(f1_idx*3)
        hd3.append(f2_idx*3)
        hd3.append(np.abs(2*f2_idx-f1_idx))
        hd3.append(np.abs(2*f1_idx-f2_idx))
        hd3.append(np.abs(2*f2_idx+f1_idx))
        hd3.append(np.abs(2*f1_idx+f2_idx))

    
        
        
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
        axs_FFT.set_xlim(0, np.amax(freq)+0.5/fs) # Add one more frequency step to the right to make the last x tick show
        axs_FFT.set_ylim(20*(np.floor(np.amin(PSD[fmask])/20)), 0)
        axs_FFT.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
        # Annotate
        if annotate is True:
            if f1_idx > len(freq)/2:
                #axs_FFT.text(freq[int(np.floor(f1_idx-0.15*data_len))], -50, "SNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits\nSFDR = "+"{:.1f}".format(SFDR)+" dBc\nSNR = "+"{:.1f}".format(SNR)+" dB\nSDR = "+"{:.1f}".format(SDR)+" dB", horizontalalignment='center', backgroundcolor='white', bbox=dict(ec='black', fc='white'))
                axs_FFT.text(freq[int(np.floor(f1_idx-0.15*data_len))], -50, "SNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits\nSFDR = "+"{:.1f}".format(SFDR)+" dBc", horizontalalignment='center', backgroundcolor='white', bbox=dict(ec='black', fc='white'))
            else:
                #axs_FFT.text(freq[int(np.floor(f1_idx+0.15*data_len))], -50, "SNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits\nSFDR = "+"{:.1f}".format(SFDR)+" dBc\nSNR = "+"{:.1f}".format(SNR)+" dB\nSDR = "+"{:.1f}".format(SDR)+" dB", horizontalalignment='center', backgroundcolor='white', bbox=dict(ec='black', fc='white'))
                axs_FFT.text(freq[int(np.floor(f1_idx+0.15*data_len))], -50, "SNDR = "+"{:.1f}".format(SNDR)+" dB\nENOB = "+"{:.2f}".format(ENOB)+" bits\nSFDR = "+"{:.1f}".format(SFDR)+" dBc", horizontalalignment='center', backgroundcolor='white', bbox=dict(ec='black', fc='white'))

        # Plot harmonics
        if numharm >= 2:
            for idx in hd2:
                axs_FFT.plot(freq[idx], PSD[idx], marker="^", mec="red", mfc="red", mew=2)
                axs_FFT.text(freq[idx], PSD[idx]+5, "2", fontweight='bold', color='red', horizontalalignment='center')
        if numharm >= 3:
            for idx in hd3:
                axs_FFT.plot(freq[idx], PSD[idx], marker="^", mec="red", mfc="red", mew=2)
                axs_FFT.text(freq[idx], PSD[idx]+5, "3", fontweight='bold', color='red', horizontalalignment='center')
                
        if annoIMD is True:
            axs_FFT.text(freq[-1], -SFDR+2.5, "SFDR = "+"{:.1f}".format(SFDR)+" dBc", color='red', horizontalalignment='right', verticalalignment='bottom', fontweight='bold')
        
        

        #datacursor(lines)
        if showNow: plt.show() 

        if save is not None: plt.savefig(save)

    
    return ENOB, SNDR, SFDR, SNR, SDR, freq, PSD, fig_FFT, axs_FFT, f1_idx


    
