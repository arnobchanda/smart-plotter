import dearpygui.dearpygui as dpg
import serial
import serial.tools.list_ports
import threading
import queue
import time
import subprocess
import sys
import re

from gui import PlotterGUI

class SmartPlotterApp:
    """
    Main application logic using Dear PyGui.
    Manages state and handles callbacks from the GUI.
    """

    def __init__(self):
        self.gui = PlotterGUI()
        self.callbacks = {
            "refresh_ports": self._handle_refresh_event,
            "update_buttons": self._update_button_states,
            "file_selected": self._handle_file_selected,
            "connect": self._handle_connect_disconnect,
            "run_program": self._handle_run_stop,
            "clear_plot": self._handle_clear_plot_event,
            "toggle_log_window": self._handle_toggle_log_window,
        }
        
        # --- State Management ---
        self.is_connected = False
        self.data_thread = None
        self.stop_thread = False
        self.data_source = None
        self.data_queue = queue.Queue()
        
        # --- Dynamic Plotting State ---
        self.max_points = 500
        self.x_data = []
        self.dynamic_series = {} 
        self.parsing_regex = None
        self.placeholder_names = []
        
        # --- Log Buffer ---
        self.log_buffer = []
        self.max_log_lines = 200


    def _get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        if not ports:
            return ["No Ports Found"]
        return [f"{port.device} - {port.description}" for port in ports]

    def _read_data_loop(self):
        """The main loop for the background data reading thread."""
        while not self.stop_thread:
            try:
                line = self.data_source.readline()
                if line:
                    self.data_queue.put(line.decode('utf-8').strip())
            except Exception:
                print("Error reading from source. Closing thread.")
                self.stop_thread = True
            time.sleep(0.01)

    def _set_ui_lock_state(self, locked: bool):
        """Locks or unlocks UI controls when connected/disconnected."""
        dpg.configure_item("-PORT_LIST-", enabled=not locked)
        dpg.configure_item("-REFRESH-", enabled=not locked)
        dpg.configure_item("-BAUD-", enabled=not locked)
        dpg.configure_item("-SCRIPT_PATH-", enabled=not locked)
        dpg.configure_item("-FORMAT-", enabled=not locked)

    def _prepare_plot_for_new_format(self):
        """
        Parses the format string, creates series, and builds a flexible regex.
        """
        self._clear_plot_series()

        format_str = dpg.get_value("-FORMAT-")
        self.placeholder_names = re.findall(r'\$\{(\w+)\}', format_str)
        
        if not self.placeholder_names:
            dpg.set_value("-STATUS-", "Error: No placeholders `${name}` found in format.")
            return False

        regex_pattern = re.escape(format_str)
        for name in self.placeholder_names:
            regex_pattern = regex_pattern.replace(
                re.escape(f'${{{name}}}'), rf'(?P<{name}>[-\d.]+)'
            )
        
        try:
            self.parsing_regex = re.compile(regex_pattern)
        except re.error as e:
            dpg.set_value("-STATUS-", f"Error: Invalid format regex - {e}")
            return False

        for name in self.placeholder_names:
            series_tag = f"series_{name}"
            dpg.add_line_series([], [], label=name, parent="y_axis", tag=series_tag)
            self.dynamic_series[name] = {"tag": series_tag, "y_data": []}
            
        dpg.fit_axis_data("y_axis")
        return True


    def _update_plot_and_log(self, line):
        """
        Parses a line of data, updates the plot, and updates the log.
        """
        # --- Update Log Buffer and UI ---
        self.log_buffer.append(f"{time.strftime('%H:%M:%S')}> {line}")
        if len(self.log_buffer) > self.max_log_lines:
            self.log_buffer.pop(0)
        dpg.set_value("-LOG_TEXT-", "\n".join(self.log_buffer))
        
        # --- NEW: Handle Auto scrolling ---
        if dpg.get_value("-LOG_AUTOSCROLL-"):
            # Setting y_scroll to -1.0 scrolls to the bottom
            dpg.set_y_scroll("-LOG_CHILD-", -1.0)


        # --- Update Plot ---
        if not self.parsing_regex: return
        
        match = self.parsing_regex.match(line)
        if not match:
            self.x_data.append(time.time())
            for name in self.placeholder_names:
                self.dynamic_series[name]["y_data"].append(float('nan'))
            return

        try:
            current_time = time.time()
            self.x_data.append(current_time)
            
            for name in self.placeholder_names:
                value_str = match.group(name)
                self.dynamic_series[name]["y_data"].append(float(value_str))

            if len(self.x_data) > self.max_points:
                self.x_data.pop(0)
                for series_info in self.dynamic_series.values():
                    series_info["y_data"].pop(0)

            for name, series_info in self.dynamic_series.items():
                dpg.set_value(series_info["tag"], [self.x_data, series_info["y_data"]])

            dpg.fit_axis_data("x_axis")
            dpg.fit_axis_data("y_axis")

        except (ValueError, IndexError, TypeError) as e:
            print(f"Could not parse line: '{line}'. Error: {e}")

    def _clear_plot_series(self):
        """Helper function to delete all dynamic series items from the plot."""
        for name, series_info in self.dynamic_series.items():
            if dpg.does_item_exist(series_info["tag"]):
                dpg.delete_item(series_info["tag"])
        self.dynamic_series.clear()

    def _handle_clear_plot_event(self):
        """Clears only the data from the plot and log."""
        print("Clearing plot data...")
        self.x_data.clear()
        for series_info in self.dynamic_series.values():
            series_info['y_data'].clear()
            dpg.set_value(series_info["tag"], [self.x_data, series_info["y_data"]])

        self.log_buffer.clear()
        dpg.set_value("-LOG_TEXT-", "Log cleared.")


    def _handle_toggle_log_window(self):
        """Callback to show/hide the log window."""
        is_visible = dpg.get_value("-SHOW_LOG-")
        dpg.configure_item("-LOG_WINDOW-", show=is_visible)


    # --- Event Handlers ---
    def _handle_refresh_event(self):
        if self.is_connected: return
        port_list = self._get_serial_ports()
        dpg.configure_item("-PORT_LIST-", items=port_list)
        self._update_button_states()

    def _handle_file_selected(self, sender, app_data):
        path = app_data['file_path_name']
        dpg.set_value("-SCRIPT_PATH-", path)
        self._update_button_states()

    def _update_button_states(self, sender=None, app_data=None):
        if self.is_connected: return
        port_selected = dpg.get_value("-PORT_LIST-")
        script_path_exists = dpg.get_value("-SCRIPT_PATH-")
        connect_enabled = port_selected and "No Ports Found" not in port_selected
        dpg.configure_item("-CONNECT-", enabled=bool(connect_enabled))
        dpg.configure_item("-RUN-", enabled=bool(script_path_exists))

    def _start_connection(self):
        if not self._prepare_plot_for_new_format():
            return False
        self.stop_thread = False
        self.data_thread = threading.Thread(target=self._read_data_loop, daemon=True)
        self.data_thread.start()
        self.is_connected = True
        self._set_ui_lock_state(locked=True)
        return True

    def _stop_connection(self):
        self.stop_thread = True
        if self.data_thread: self.data_thread.join()
        if self.data_source:
             if isinstance(self.data_source, serial.Serial): self.data_source.close()
             else: self.process.terminate()
        self.is_connected = False
        self.data_source = None
        self._set_ui_lock_state(False)
        self._update_button_states()

    def _handle_connect_disconnect(self):
        if self.is_connected:
            self._stop_connection()
            dpg.set_value("-STATUS-", "Status: Disconnected")
            dpg.configure_item("-CONNECT-", label="Connect")
        else:
            full_port_string = dpg.get_value('-PORT_LIST-')
            port = full_port_string.split(' ')[0]
            baud = int(dpg.get_value('-BAUD-'))
            try:
                self.data_source = serial.Serial(port, baud, timeout=1)
                if self._start_connection():
                    dpg.set_value("-STATUS-", f"Status: Connected to {port}")
                    dpg.configure_item("-CONNECT-", label="Disconnect")
                else:
                    self.data_source.close()
            except serial.SerialException as e:
                dpg.set_value("-STATUS-", f"Error: {e}")

    def _handle_run_stop(self):
        if self.is_connected:
            self._stop_connection()
            dpg.set_value("-STATUS-", "Status: Program stopped")
            dpg.configure_item("-RUN-", label="Run Program")
        else:
            script = dpg.get_value('-SCRIPT_PATH-')
            command = [sys.executable, script]
            try:
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
                self.data_source = self.process.stdout
                if self._start_connection():
                    dpg.set_value("-STATUS-", f"Status: Running {script.split('/')[-1]}")
                    dpg.configure_item("-RUN-", label="Stop Program")
            except Exception as e:
                dpg.set_value("-STATUS-", f"Error: {e}")

    def run(self):
        self.gui.create_viewport()
        self.gui.setup_ui(self.callbacks) 
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        self._handle_refresh_event()
        
        while dpg.is_dearpygui_running():
            try:
                for _ in range(self.data_queue.qsize()):
                    line = self.data_queue.get_nowait()
                    self._update_plot_and_log(line)
            except queue.Empty:
                pass
            dpg.render_dearpygui_frame()
        
        self._stop_connection()
        dpg.destroy_context()

