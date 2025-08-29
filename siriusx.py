import opendaq
import numpy as np

class SiriusX():
    """
    A high-level interface for configuring and acquiring data from Dewesoft 
    Sirius X data acquisition devices using the opendaq API.

    This class provides methods to:
    - List and connect to available Sirius X devices.
    - Configure device channels for various measurement types (e.g., IEPE, Voltage).
    - Set and get sample rates.
    - Acquire raw or sensitivity-corrected (processed) data from selected channels.
    - Manage multi-channel data reading and buffer handling.
    
    Basic Usage
    -----------
    Examples
    --------
    >>> import opendaq
    >>> from siriusx import SiriusX
    >>> sx = SiriusX()
    >>> sx.list_available_devices()
    Name: SiriusX-1 Connection string: daq.sirius://192.168.1.100
    >>> sx.connect("daq.sirius://192.168.1.100")
    True
    >>> sx.set_sample_rate(1000)
    1000.0
    >>> channel_settings = {
    ...     0: {
    ...         'Name': 'acc_X',
    ...         'Measurement': 'IEPE',
    ...         'Range': 10000,
    ...         'HPFilter': 'AC 1Hz',
    ...         'Excitation': 2.0,
    ...         'Sensitivity': 100,
    ...         'Sensitivity Unit': 'mV/g',
    ...         'Unit': 'g',
    ...     },
    ... }
    >>> sx.configure_channels(channel_settings)
    >>> # Acquire 2 seconds of processed data as a dictionary
    >>> data_dict = sx.acquire_processed(acquisition_time=2.0, return_dict=True)
    """

    def __init__(self):
        """
        Initialize SiriusX instance.
        """
        self.instance = opendaq.Instance()
        self.device = None
        self.connected = False
        self.sample_rate = None

        self.active_signals = set()

    def list_available_devices(self, print_devices=True, return_list=False):
        """
        List available devices.

        Parameters
        ----------
        print_devices : bool, optional
            Print device info to stdout.
        return_list : bool, optional
            Return list of devices.

        Returns
        -------
        list or None
            List of devices if return_list is True.
        """

        available_devices = []

        for device_info in self.instance.available_devices:
            if print_devices:
                print("Name:", device_info.name, "Connection string:", 
                      device_info.connection_string)
            available_devices.append(
                ("Name:", device_info.name, "Connection string:", 
                 device_info.connection_string)
                )

        if return_list:
            return available_devices
    
    def connect(self, connection_string):
        """
        Connect to a device.

        Parameters
        ----------
        connection_string : str
            Device connection string.

        Returns
        -------
        bool
            True if connected, False otherwise.
        """
        try:
            self.device = self.instance.add_device(connection_string)
            self.connected = True
            return True
        except Exception as e:
            print("Error connecting to device:", e)
            self.connected = False
            return False
    
    def get_sample_rate(self):
        """
        Get current sample rate.

        Returns
        -------
        float
            Sample rate in Hz.
        """
        self.sample_rate = self.device.get_property_value("SampleRate")
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        """
        Set sample rate. The device has a limited range and discrete steps. 
        The method will return the sample_rate that was actually set.

        Parameters
        ----------
        sample_rate : float
            Desired sample rate in Hz.

        Returns
        -------
        float
            Set sample rate in Hz.
        """
        self.device.set_property_value("SampleRate", sample_rate)
        return self.get_sample_rate()

    def get_available_channels(self):
        """
        Get all available channels.

        Returns
        -------
        list
            List of channel objects.
        """
        self.channels = list(self.device.channels_recursive)
        return self.channels

    def list_available_channels(self):
        """
        Print all available channels and their properties.
        """
        self.channels = self.get_available_channels()

        for chan in self.channels:
            print('Channel Global ID: ', chan.global_id)
            print('Channel Name     : ', chan.name)
            for func_block in chan.get_function_blocks():
                print('  Function Block Name: ', func_block.name)
                for prop in func_block.visible_properties:

                    property_name = prop.name
                    current_value = prop.value
                    selection_values = prop.selection_values
                    human_readable_value = selection_values[current_value] if selection_values is not None else current_value
                    unit = r'' if prop.unit is None else prop.unit.symbol

                    print('    ', f'{property_name:20s}', ':', f'{str(human_readable_value):10s}', selection_values, unit)
    
    def get_available_ai_signals(self):
        """
        Get all available AI signals.

        Returns
        -------
        list
            List of AI signal objects.
        """
        self.available_ai_signals = []
        all_signals = self.device.signals_recursive
        for signal in all_signals:
            if 'AI ' in signal.name:
                self.available_ai_signals.append(signal)
        return self.available_ai_signals

    def _configure_channel(self, channel_num: int, settings: dict):
        """
        
        Parameters
        ----------
        channel_num : int
            The channel number to configure.
        settings : dict
            A dictionary containing the settings for the channel.
            Example for IEPE:
            ```
            settings = {
                'Name': 'acc_X',
                'Measurement': 'IEPE', # [IEPE, Voltage]
                'Range': 10000, # [10000, 5000, 1000, 200] mV
                'HPFilter': 'AC 1Hz', # [AC 0.1Hz, AC 1Hz]
                'Excitation': 2.0, # [2, 4, 6] mA
                'Sensitivity': 100,
                'Sensitivity Unit': 'mV/g', # [mV/g, mV/(m/s^2)]
                'Unit': 'g', # [g, m/s^2]
            }
            ```
            Example for Voltage:
            ```
            settings = {
                'Name': 'vol_1',
                'Measurement': 'Voltage', # [IEPE, Voltage]
                'Range': 10, # [10, 5, 1, 0.2] V
                'HPFilter': 'DC', # [DC, AC 0.1Hz, AC 1Hz] 
                'Sensitivity': 1,
                'Sensitivity Unit': 'V/V', # [arbitrary]
                'Unit': 'V', # [arbitrary]
            }
            ```
        """
        #self.channel_settings[channel_num] = settings
        #self.active_signals.add(self.available_ai_signals[channel_num])

        channels = self.get_available_channels()
        selected_channel = channels[channel_num]

        selected_channel.name = settings.get('Name', selected_channel.name)

        amplifier = selected_channel.get_function_blocks()[0]
        for prop in amplifier.visible_properties:
            property_name = prop.name
            if property_name in settings:
                new_setting = settings[property_name] # human readable setting
                available_values = list(prop.selection_values) # human readable values
                # check if the setting is available
                if new_setting in available_values:
                    # set the value of the property as the index of the new setting
                    prop.value = available_values.index(new_setting)
                else:
                    print(
                        f"Setting '{new_setting}' not available for property '{property_name}'"
                        f"Available values are: {available_values}"
                        )

    def configure_channels(self, channel_settings: dict):
        """
        Configure multiple channels.

        Parameters
        ----------
        channel_settings : dict
            A dictionary containing the settings for each channel.
            Example:
            ```
            channel_settings = {
                0: {
                    'Name': 'acc_X',
                    'Measurement': 'IEPE', # [IEPE, Voltage]
                    'Range': 10000, # [10000, 5000, 1000, 200] mV
                    'HPFilter': 'AC 1Hz', # [AC 0.1Hz, AC 1Hz]
                    'Excitation': 2.0, # [2, 4, 6] mA
                    'Sensitivity': 100,
                    'Sensitivity Unit': 'mV/g', # [mV/g, mV/(m/s^2)]
                    'Unit': 'g', # [g, m/s^2]
                },
                1: {
                    'Name': 'vol_1',
                    'Measurement': 'Voltage', # [IEPE, Voltage]
                    'Range': 10, # [10, 5, 1, 0.2] V
                    'HPFilter': 'DC', # [DC, AC 0.1Hz, AC 1Hz] 
                    'Sensitivity': 1,
                    'Sensitivity Unit': 'V/V', # [arbitrary]
                    'Unit': 'V', # [arbitrary]
                }
            }            
            ```
            Keys must be integers representing channel numbers of the Sirius X 
            device.
        """
        self.channel_settings = channel_settings

        # setting channels
        for channel_num, settings in channel_settings.items():
            self._configure_channel(channel_num, settings)

        # get all ai signals
        ai_signals = self.get_available_ai_signals()

        # get selected signals
        self.selected_channels = list(channel_settings.keys())
        self.selected_signals = [ai_signals[i] for i in self.selected_channels]

    def create_reader(self):
        """
        Create a multi-signal reader for selected channels.
        """
        # create multi reader with selected signals
        self.multi_reader = opendaq.MultiReader(
            signals=self.selected_signals,
            timeout_type=opendaq.ReadTimeoutType.All,
        )
    
    def start_reader(self):
        """
        Start the multi-signal reader.
        """
        _ = self.multi_reader.read(count=0, timeout_ms=10)

    def read_raw(self, sample_count, timeout):
        """
        Read raw data from the device.

        Parameters
        ----------
        sample_count : int
            Number of samples to read.
        timeout : float
            Timeout in seconds.

        Returns
        -------
        ndarray
            Raw data array.
        """
        # read raw data from the multi reader
        raw_data = self.multi_reader.read(
            count=sample_count,
            timeout_ms=int(1000*timeout)
        )
        # transpose
        raw_data = raw_data.T
        return raw_data

    def read_processed(self, sample_count, timeout):
        """
        Read and process data (apply sensitivity).

        Parameters
        ----------
        sample_count : int
            Number of samples to read.
        timeout : float
            Timeout in seconds.

        Returns
        -------
        ndarray
            Processed data array.
        """
        # read raw data
        raw_data = self.read_raw(
            sample_count=sample_count,
            timeout=timeout
        )
        # apply sensitivity
        processed_data = []
        for sig_num, ch_num in enumerate(self.channel_settings.keys()):
            signal = raw_data[:, sig_num]
            processed_ch = self._apply_sensitivity(ch_num=ch_num, signal=signal)
            processed_data.append(processed_ch)
        processed_data = np.array(processed_data)
        # tranpose
        processed_data = processed_data.T
        return processed_data

    def available_samples(self):
        """
        Get number of available samples in the reader (device buffer).

        Returns
        -------
        int
            Number of available samples.
        """
        return self.multi_reader.available_count

    def stop_reader(self):
        """
        Stop and clean up the reader.
        """
        self.multi_reader = None

    def acquire_raw(self, sample_count, timeout):
        """
        Acquire raw data in a single operation.

        Parameters
        ----------
        sample_count : int
            Number of samples to acquire.
        timeout : float
            Timeout in seconds.

        Returns
        -------
        ndarray
            Raw data array.
        """

        self.create_reader()
        self.start_reader()

        # acquire raw data
        raw_data = self.read_raw(
            sample_count=sample_count,
            timeout=timeout
        )

        self.stop_reader()

        return raw_data
    
    def acquire_processed(self, acqusition_time, return_dict=False):
        """
        Acquire and process data for a given time.

        Parameters
        ----------
        acqusition_time : float
            Acquisition time in seconds.
        return_dict : bool, optional
            If True, return dict with channel names and units.

        Returns
        -------
        ndarray or dict
            Processed data array or dict.
        """

        # calc required samples
        sample_rate = self.get_sample_rate()
        sample_count = int(acqusition_time * sample_rate)

        # acquire raw data
        raw_data = self.acquire_raw(
            sample_count=sample_count, 
            timeout=2*acqusition_time)

        # apply sensitivity
        processed_data = []
        for sig_num, ch_num in enumerate(self.channel_settings.keys()):
            signal = raw_data[:, sig_num]
            processed_ch = self._apply_sensitivity(ch_num=ch_num, signal=signal)
            processed_data.append(processed_ch)
        processed_data = np.array(processed_data)

        if return_dict:
            data_dict = {}
            # populate the dict with processed channel data
            for sig_num, ch_num in enumerate(self.channel_settings.keys()):
                ch_name = self.channel_settings[ch_num]['Name']
                ch_unit = self.channel_settings[ch_num]['Unit']
                data_dict[ch_name] = {
                    'signal': processed_data[sig_num],
                    'unit': ch_unit,
                }
            # create time signal
            sample_rate = self.get_sample_rate()
            time_sig = np.linspace(0, acqusition_time, sample_count)
            data_dict['time'] = {'signal': time_sig, 'unit': 's'}
            return data_dict

        else:
            # transpose and return
            processed_data = processed_data.T
            return processed_data
    
    def _apply_sensitivity(self, ch_num: int, signal):

        # get sensitivity and units
        sens = self.channel_settings[ch_num]['Sensitivity']
        unit_output = self.channel_settings[ch_num]['Unit']
        sens_unit = self.channel_settings[ch_num]['Sensitivity Unit']
        sens_unit_output = sens_unit.split('/')[-1].strip('()')

        # apply sensitivity
        processed_signal = signal / sens

        # acceleration
        if unit_output in ['g', 'm/s^2']:
            # sens and output unit are the same
            if unit_output == sens_unit_output:
                pass
            elif unit_output=='g' and sens_unit_output=='m/s^2':
                g = 9.81
                processed_signal = processed_signal / g
            elif unit_output=='m/s^2' and sens_unit_output=='g':
                g = 9.81
                processed_signal = processed_signal * g
            else:
                print(f'Units were not handled: '
                      f'unit_output set to {unit_output} and '
                      f'sensitivity unit is {sens_unit}.')
            return processed_signal

        # voltage
        elif unit_output in ['V']:
            return processed_signal

        # arbitrary
        else:
            return processed_signal

