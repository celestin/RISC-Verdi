"""
Copyright 2018-2019 Dover Microsystems, Inc.

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import tkinter as tk

class Interface():
    """Methods for communicating with Verdi"""

    def __init__(self):

        self.tk = tk.Tk(className='wave_interface')

        # Keep the default Tk window hidden, GUI not needed here.
        self.tk.overrideredirect(1)
        self.tk.withdraw()

        # Get the name of this app from Tk's point of view.
        self.tk_name = self.tk.winfo_name()

        # Assign to none until callback is registered.
        self.time_change_name = None

        # The Verdi/nWave Tk interpreter instance name.
        self.wave_tk_name = None

        # List of local functions to execute when a time change
        # callback occurs.
        self.time_change_work_list = []

        # No filename until the wave app is known.
        self.wave_filename = None

        # Find candidates for the wave app's Tk name.
        base_names = {'verdi', 'nWave'}
        self.candidates = []
        for interp in self.tk.winfo_interps():
            for base_name in base_names:
                if base_name in interp:
                    self.candidates.append(interp)

    # ------------------------------------------------------------
    # Verdi Command Language command wrappers.
    #
    # Many of the Verdi commands have additional switches
    # These wrappers do not handle.  A future optimization
    # could support the full set of switches.
    # ------------------------------------------------------------

    def wvGetActiveFileName(self):
        filename = self.tk.send(self.wave_tk_name,
                                'wvGetActiveFileName')

        assert(len(filename) != 0), 'No fsdb filename returned.'

        return filename

    def wvGetSigValueByTime(self, signal):
        return self.tk.send(self.wave_tk_name,
                            'wvGetSigValueByTime',
                            signal)

    def wvGetCursor(self):
        result = self.tk.send(self.wave_tk_name,
                              'wvGetCursor')

        assert(result != '0'), 'wvGetCursor failure.'

        # [0] Success = 1
        # [1] Time
        # [2] 'x'
        # [3] Timescale
        return {'time':      result.split(' ')[1],
                'timescale': result.split(' ')[3]}

    def wvSetCursor(self, time):
        result = self.tk.send(self.wave_tk_name,
                              'wvSetCursor',
                              time)
        assert(result != '0'), 'wvSetCursor failure.'

    def wvCenterCursor(self):
        result = self.tk.send(self.wave_tk_name,
                              'wvCenterCursor')
        assert(result != '0'), 'wvCenterCursor failure.'

    def wvSetSearchMode(self, *args):
        result = self.tk.send(self.wave_tk_name,
                              'wvSetSearchMode',
                              args)
        assert(result != '0'), 'Could not set search mode.'

    def wvSearchBySignal(self, direction, signal, time):
        assert(direction in {'Next', 'Prev'}), 'Illegal direction.'

        cmd = 'wvSearch' + direction + 'BySignal'
        delim_option = '-delim /'
        time_option  = '-time ' + time
        result = self.tk.send(self.wave_tk_name,
                              cmd,
                              signal,
                              delim_option,
                              time_option)

        # [0] Success = 1
        # [1] Time
        if result == '0':
            new_time = None
        else:
            new_time = result.split(' ')[1]

        return new_time

    def AddEventCallback(self, callback, reason, asynchronous=1):
        self.tk.send(self.wave_tk_name,
                     'AddEventCallback',
                     self.tk_name,
                     callback,
                     reason,
                     asynchronous)

    def RemoveEventCallback(self, callback, reason):
        self.tk.send(self.wave_tk_name,
                     'RemoveEventCallback',
                     self.tk_name,
                     callback,
                     reason)

    # ------------------------------------------------------------
    # Simple getters and setters.
    # ------------------------------------------------------------

    def get_candidates_for_wave_tk_name(self):
        """Return a list of possible Verdi app names"""
        return self.candidates

    def set_wave_tk_name(self, wave_tk_name):
        self.wave_tk_name = wave_tk_name

    def get_wave_tk_name(self):
        return self.wave_tk_name

    def get_wave_filename(self):
        """Return the fsdb filename"""
        if self.wave_filename is None:
            # Find the wave filename.  Use this as a barometer
            # for the success of communicaiton with Verdi.
            self.wave_filename = self.wvGetActiveFileName()

        return self.wave_filename

    def get_sig_value_by_time(self, signal):
        esc_sig = self.escape_signal(signal)
        return self.wvGetSigValueByTime(esc_sig)

    def get_time_at_cursor(self):
        result = self.wvGetCursor()
        return result['time']

    # ------------------------------------------------------------
    # Application specific 
    # ------------------------------------------------------------

    def escape_signal(self, signal):
        new_signal = ''
        for ch in signal:
            if ch in {'[', ']'}:
                new_signal += '\\'
            new_signal += ch
        return new_signal

    def search_signal_change(self, signal, direction):
        self.wvSetSearchMode('-anyChange')
        esc_sig = self.escape_signal(signal)
        time = self.get_time_at_cursor()
        new_time = self.wvSearchBySignal(direction=direction,
                                         signal=esc_sig,
                                         time=time)
        if new_time is not None:
            self.wvSetCursor(new_time)
            self.wvCenterCursor()

    def time_change_callback(self, *args):
        """Called by Verdi when its cursor moves"""

        # Argument format:
        # [0] wvCursorTimeChange
        # [1] time at cursor
        # [2] path to signal clocked
        # [3] fsdb file path
        reasons = {'wvCursorTimeChange'}
        assert(args[0] in reasons), 'Unknown callback reason.'

        # Step through the work list (array of functions)
        # and call each one with the given arguments.
        for work in self.time_change_work_list:
            work(args[1])

    def register_time_change_callback(self):
        """Add a cursor time change callback to Verdi"""

        self.time_change_name = 'time_change_callback'

        self.tk.createcommand(self.time_change_name,
                              self.time_change_callback)

        self.AddEventCallback(callback=self.time_change_name,
                              reason='wvCursorTimeChange')

    def unregister_time_change_callback(self):
        """Remove the callback connection to clean up"""

        if self.time_change_name is not None:
            self.RemoveEventCallback(callback=self.time_change_name,
                                     reason='wvCursorTimeChange')

    def add_time_change_work(self, *args):
        """Add functions to the time change callback work list"""
        for arg in args:
            self.time_change_work_list.append(arg)
            
    def cleanup(self):
        self.unregister_time_change_callback()
        self.tk.destroy()
