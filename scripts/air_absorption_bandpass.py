from filter import FilterStrategy
import numpy as np
from scipy.signal import butter, lfilter
import air_absorption_calculation as aa
import threading


class Bandpass(FilterStrategy):

    def __init__(self, max_frequency=20000, min_frequency=1, divisions=50, fs=44100):
        self.max_frequency = max_frequency
        self.min_frequency = min_frequency
        self.divisions = divisions
        self.fs = fs
        self.NAME="Bandpass"

    '''
    Calculates how much distance the sound has travelled. [m]
    '''

    def distance_travelled(self, sample_number, sampling_frequency, c):
        seconds_passed = sample_number*(sampling_frequency**(-1))
        return (seconds_passed*c)  # [m]

    '''
    Returns a butterworth bandpass filter.
    '''

    def create_bandpass_filter(self, lowcut, highcut, fs, order=4):
        nyq = 0.5 * fs
        low = (lowcut / nyq)
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='bandpass')
        return b, a

    '''
    Applies a butterworth bandpass filter.
    '''

    def apply_bandpass_filter(self, data, lowcut, highcut, fs, order=3):
        b, a = self.create_bandpass_filter(lowcut, highcut, fs, order=order)
        y = lfilter(b, a, data)
        return y

    def apply_single_band(self, IR, band_num, frequency_range, combined_signals):
        # Upper ceiling of each band
        band_max = ((frequency_range / self.divisions) * band_num)

        # Lower ceiling of each band and handling of edge case
        if band_num == 1:
            band_min = self.min_frequency
        else:
            band_min = ((frequency_range / self.divisions) * (band_num - 1))

        # Calculating mean frequency of band which determines the attenuation.
        band_mean = (band_max+band_min)/2
        print(f"Band {band_num} frequencies: min: {band_min} max: {band_max} mean:{band_mean}")

        # Prepare + apply bandpass filter
        filtered_signal = self.apply_bandpass_filter(
            IR, band_min, band_max, self.fs, 3)

        # Apply attenuation
        for k in range(0, len(filtered_signal)):
            alpha, alpha_iso, c, c_iso = aa.air_absorption(band_mean)
            distance = self.distance_travelled(k, self.fs, c)
            attenuation = distance*alpha  # [dB]

            filtered_signal[k] *= 10**(-attenuation / 10)
        
        
        # Summing the different bands together
        for k in range(0, len(combined_signals)):
            combined_signals[k] += filtered_signal[k]


    # max_frequency, min_frequency, divisions, fs
    def air_absorption_bandpass(self, IR):
        frequency_range = self.max_frequency - self.min_frequency

        combined_signals = np.zeros(len(IR))
        
        threads = []
        
        # Divide frequency range into defined frequency bands
        for j in range(1, self.divisions + 1):
            t = threading.Thread(target=self.apply_single_band, args=(IR, j, frequency_range, combined_signals, ))
            t.start()

            threads.append(t)

        # join all threads
        for t in threads:
            t.join()

        return combined_signals

    def apply(self, IR):
        return self.air_absorption_bandpass(IR)
