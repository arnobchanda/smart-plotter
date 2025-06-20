import dearpygui.dearpygui as dpg
import os
import requests

class PlotterGUI:
    def __init__(self):
        dpg.create_context()
        self._load_and_bind_font()

    def _load_and_bind_font(self):
        font_file = "JetBrainsMono-Regular.ttf"
        font_url = f"https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/{font_file}"
        if not os.path.exists(font_file):
            print(f"Downloading font: {font_file}...")
            try:
                response = requests.get(font_url)
                response.raise_for_status()
                with open(font_file, "wb") as f:
                    f.write(response.content)
                print("Font downloaded successfully.")
            except requests.exceptions.RequestException as e:
                print(f"Error downloading font: {e}")
                return

        with dpg.font_registry():
            try:
                default_font = dpg.add_font(font_file, 16)
                dpg.bind_font(default_font)
                print("JetBrains Mono font bound successfully.")
            except Exception as e:
                print(f"Error loading font: {e}")

    def create_viewport(self):
        dpg.create_viewport(
            title="Smart Serial Plotter - V1.9 (Dear PyGui)",
            width=1200,
            height=800
        )

    def _sync_child_heights_to_plot(self, sender, app_data, user_data):
        try:
            _, plot_height = dpg.get_item_rect_size(user_data["plot_tag"])
            row_height = int(plot_height / 3)
            adjusted_row_height  = row_height - 3  # Adjust for spacing
            for tag in user_data["row_tags"]:
                dpg.configure_item(tag, height=adjusted_row_height)
            
        except KeyError:
            pass

    def setup_ui(self, app_callbacks):
        with dpg.window(label="Main Window", tag="primary_window", autosize=True, no_resize=False, no_move=False, width=1300, no_scrollbar=True):
            with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchSame):
                dpg.add_table_column(width_fixed=True, init_width_or_weight=600)
                dpg.add_table_column(width_stretch=True, width=800)

                with dpg.table_row():
                    row_tags = []

                    with dpg.table_cell():
                        with dpg.table(header_row=False, tag="left_column_table"):
                            dpg.add_table_column()

                            for i in range(3):
                                with dpg.table_row():
                                    tag = f"child_row_{i}"
                                    row_tags.append(tag)
                                    with dpg.child_window(tag=tag, autosize_x=True, no_scrollbar=True):
                                        if i == 0:
                                            with dpg.tab_bar(tag="-TAB_GROUP-"):
                                                with dpg.tab(label="Serial Port"):
                                                    dpg.add_text("Available Serial Ports:")
                                                    dpg.add_listbox(items=[], tag="-PORT_LIST-", num_items=5, callback=app_callbacks["update_buttons"])
                                                    dpg.add_combo(items=['9600', '19200', '38400', '57600', '115200'], label="Baud Rate", default_value='115200', tag="-BAUD-")
                                                    dpg.add_button(label="Refresh Port List", callback=app_callbacks["refresh_ports"], tag="-REFRESH-", width=-1)

                                                with dpg.tab(label="Program Output"):
                                                    dpg.add_text("Select a Python script to run:")
                                                    with dpg.group(horizontal=True):
                                                        dpg.add_input_text(tag="-SCRIPT_PATH-", width=-80, callback=app_callbacks["update_buttons"])
                                                        dpg.add_button(label="Browse", callback=lambda: dpg.show_item("file_dialog_id"))
                                                    dpg.add_button(label="Run Program", tag="-RUN-", callback=app_callbacks["run_program"], enabled=False, width=-1)

                                        elif i == 1:
                                            dpg.add_text("Data Output Template:")
                                            dpg.add_input_text(tag="-FORMAT-", default_value="Temp: ${temp}, Hum: ${humidity}", label="", width=-1)
                                            dpg.add_text("Use ${name} to define a variable.", color=(200, 200, 200))
                                            with dpg.group(horizontal=True):
                                                dpg.add_checkbox(label="Show Raw Output", tag="-SHOW_LOG-", callback=app_callbacks["toggle_log_window"])
                                                dpg.add_checkbox(label="Autoscroll Output", tag="-LOG_AUTOSCROLL-", default_value=True)
                                            dpg.add_button(label="Connect", tag="-CONNECT-", callback=app_callbacks["connect"], enabled=False, width=-1)

                                        else:
                                            dpg.add_text("Plot Controls")
                                            dpg.add_separator()
                                            with dpg.group(tag="-VARIABLE_CONTROLS-"):
                                                pass
                                            dpg.add_separator()
                                            dpg.add_button(label="Clear Plot", callback=app_callbacks["clear_plot"], width=-1, tag="-CLEAR_PLOT-")
                                            dpg.add_text("Status: Disconnected", tag="-STATUS-")

                    with dpg.table_cell():
                        with dpg.plot(label="Real-time Data Plot", height=-1, width=-1, tag="-PLOT-"):
                            dpg.add_plot_legend()
                            # THE FIX: Ensure the X-axis is a standard axis, not a time axis.
                            dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="x_axis", time=True)
                            dpg.add_plot_axis(dpg.mvYAxis, label="Value", tag="y_axis")

        with dpg.window(label="Raw Data Log", tag="-LOG_WINDOW-", show=False, width=600, height=250, pos=(100, 100)):
            with dpg.child_window(tag="-LOG_CHILD-", autosize_x=True, autosize_y=True):
                 dpg.add_text("Waiting for data...", tag="-LOG_TEXT-", wrap=580)

        with dpg.file_dialog(
            directory_selector=False, show=False, callback=app_callbacks["file_selected"], 
            tag="file_dialog_id", width=400, height=300):
            dpg.add_file_extension(".py", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*")

        with dpg.item_handler_registry(tag="plot_resize_handler"):
            dpg.add_item_resize_handler(callback=self._sync_child_heights_to_plot,
                                         user_data={"plot_tag": "-PLOT-", "row_tags": row_tags})
        dpg.bind_item_handler_registry("-PLOT-", "plot_resize_handler")

    def run_ui(self):
        self.create_viewport()
        self.setup_ui(app_callbacks={
            "update_buttons": lambda: None,
            "refresh_ports": lambda: None,
            "connect": lambda: None,
            "run_program": lambda: None,
            "toggle_log_window": lambda: None,
            "clear_plot": lambda: None,
            "file_selected": lambda s, a: None,
            "toggle_separate_axis": lambda: None,
        })
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

if __name__ == "__main__":
    gui = PlotterGUI()
    gui.run_ui()
