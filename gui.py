import dearpygui.dearpygui as dpg
import os
import requests

class PlotterGUI:
    """
    This class is responsible for creating the GUI window and its layout
    using the Dear PyGui library.
    """

    def __init__(self):
        dpg.create_context()
        self._load_and_bind_font()

    def _load_and_bind_font(self):
        """
        Downloads JetBrains Mono font if not present, then loads and
        binds it as the default font for the application.
        """
        font_file = "JetBrainsMono-Regular.ttf"
        font_url = f"https://github.com/JetBrains/JetBrainsMono/raw/refs/heads/master/fonts/ttf/{font_file}"
        
        # --- Download the font if it doesn't exist ---
        if not os.path.exists(font_file):
            print(f"Downloading font: {font_file}...")
            try:
                response = requests.get(font_url)
                response.raise_for_status()  # Raise an exception for bad status codes
                with open(font_file, "wb") as f:
                    f.write(response.content)
                print("Font downloaded successfully.")
            except requests.exceptions.RequestException as e:
                print(f"Error downloading font: {e}")
                # If download fails, we won't try to load it.
                # Dear PyGui will use its default font.
                return

        # --- Load and bind the font ---
        with dpg.font_registry():
            try:
                default_font = dpg.add_font(font_file, 19)
                dpg.bind_font(default_font)
                print("JetBrains Mono font bound successfully.")
            except Exception as e:
                print(f"Error loading font: {e}")


    def create_viewport(self):
        """Creates the main application window (viewport)."""
        dpg.create_viewport(
            title="Smart Plotter (V0.4.0)",
            width=700,
            height=500
        )

    def setup_ui(self, app_callbacks):
        """
        Sets up the primary window and all UI elements.
        Callbacks from the main app are passed in to link UI to logic.
        """
        with dpg.window(label="Main Window", tag="primary_window"):
            with dpg.tab_bar():
                # --- Serial Port Tab ---
                with dpg.tab(label="Serial Port"):
                    dpg.add_text("Available Serial Ports:")
                    dpg.add_listbox(
                        items=[], 
                        tag="-PORT_LIST-", 
                        num_items=5, 
                        callback=app_callbacks["update_buttons"]
                    )
                    dpg.add_button(
                        label="Refresh", 
                        callback=app_callbacks["refresh_ports"], 
                        tag="-REFRESH-"
                    )
                    dpg.add_combo(
                        items=['9600', '19200', '38400', '57600', '115200'],
                        label="Baud Rate",
                        default_value='115200',
                        tag="-BAUD-"
                    )
                    dpg.add_button(
                        label="Connect", 
                        tag="-CONNECT-", 
                        callback=app_callbacks["connect"],
                        enabled=False
                    )

                # --- Program Output Tab ---
                with dpg.tab(label="Program Output"):
                    dpg.add_text("Select a Python script to run:")
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(tag="-SCRIPT_PATH-", width=-80)
                        dpg.add_button(
                            label="Browse", 
                            callback=lambda: dpg.show_item("file_dialog_id")
                        )
                    dpg.add_button(
                        label="Run Program", 
                        tag="-RUN-", 
                        callback=app_callbacks["run_program"],
                        enabled=False
                    )

            # --- Status Bar ---
            dpg.add_separator()
            dpg.add_text("Status: Disconnected", tag="-STATUS-")

        # --- Setup File Dialog (initially hidden) ---
        with dpg.file_dialog(
            directory_selector=False, 
            show=False, 
            callback=app_callbacks["file_selected"], 
            tag="file_dialog_id",
            width=400, height=300):
            dpg.add_file_extension(".py", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*")

