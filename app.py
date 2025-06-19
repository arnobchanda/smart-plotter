import dearpygui.dearpygui as dpg
import serial.tools.list_ports

from gui import PlotterGUI

class SmartPlotterApp:
    """
    Main application logic using Dear PyGui.
    Manages state and handles callbacks from the GUI.
    """

    def __init__(self):
        # The GUI class now handles dpg context creation and font loading
        self.gui = PlotterGUI()
        
        # A dictionary to hold references to our callback methods
        self.callbacks = {
            "refresh_ports": self._handle_refresh_event,
            "update_buttons": self._update_button_states,
            "file_selected": self._handle_file_selected,
            "connect": self._handle_connect_event,
            "run_program": self._handle_run_event
        }

    def _get_serial_ports(self):
        """
        Scans for and returns a list of available serial ports,
        formatted with both device name and description.
        """
        ports = serial.tools.list_ports.comports()
        if not ports:
            return ["No Ports Found"]
        # Create a user-friendly string for each port
        return [f"{port.device} - {port.description}" for port in ports]

    # --- Callback Methods ---

    def _handle_refresh_event(self):
        """Callback for the 'Refresh' button."""
        print("Refreshing ports...")
        port_list = self._get_serial_ports()
        dpg.configure_item("-PORT_LIST-", items=port_list)
        self._update_button_states()

    def _handle_file_selected(self, sender, app_data):
        """Callback for the file dialog."""
        path = app_data['file_path_name']
        dpg.set_value("-SCRIPT_PATH-", path)
        self._update_button_states()

    def _update_button_states(self):
        """Enable or disable buttons based on the current UI state."""
        port_selected = dpg.get_value("-PORT_LIST-")
        script_path_exists = dpg.get_value("-SCRIPT_PATH-")
        
        connect_enabled = port_selected and "No Ports Found" not in port_selected
        dpg.configure_item("-CONNECT-", enabled=bool(connect_enabled))

        dpg.configure_item("-RUN-", enabled=bool(script_path_exists))

    def _handle_connect_event(self):
        """Placeholder callback for the 'Connect' button."""
        full_port_string = dpg.get_value('-PORT_LIST-')
        port = full_port_string.split(' ')[0]
        
        baud = dpg.get_value('-BAUD-')
        print(f"Attempting to connect to {port} at {baud} baud.")
        dpg.set_value("-STATUS-", f"Status: Connecting to {port}...")

    def _handle_run_event(self):
        """Placeholder callback for the 'Run Program' button."""
        script = dpg.get_value('-SCRIPT_PATH-')
        print(f"Attempting to run script: {script}")
        dpg.set_value("-STATUS-", "Status: Running program...")
        
    def run(self):
        """Sets up and runs the Dear PyGui application."""
        self.gui.create_viewport()
        self.gui.setup_ui(self.callbacks) 
        
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        
        self._handle_refresh_event()
        
        dpg.start_dearpygui()
        
        dpg.destroy_context()

