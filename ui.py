import time
from windows import synchronize_window_size
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import automation as core
import config
import windows
import state
import cv2
import pyautogui
from PIL import Image, ImageTk
import state
import automation as core
import config
import profiles
import workers

class RegionSelector:
    def __init__(self, parent, title):
        self.result = None

        first = windows.get_window(config.FIRST_WINDOW)
        windows.bring_to_front(first)
        time.sleep(0.2)

        screenshot = pyautogui.screenshot(
            region=(
                first.left,
                first.top,
                first.width,
                first.height,
            )
        )

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.attributes("-topmost", True)

        max_width = 1000
        max_height = 700

        self.scale = min(
            1.0,
            max_width / first.width,
            max_height / first.height,
        )

        display_width = int(first.width * self.scale)
        display_height = int(first.height * self.scale)

        screenshot = screenshot.resize(
            (display_width, display_height)
        )

        self.image = ImageTk.PhotoImage(screenshot)

        self.canvas = tk.Canvas(
            self.window,
            width=display_width,
            height=display_height,
            cursor="crosshair",
        )
        self.canvas.pack()

        self.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.image,
        )

        self.canvas.bind(
            "<ButtonPress-1>",
            self.mouse_down,
        )
        self.canvas.bind(
            "<B1-Motion>",
            self.mouse_move,
        )
        self.canvas.bind(
            "<ButtonRelease-1>",
            self.mouse_up,
        )

        tk.Label(
            self.window,
            text=f"Drag around the {title.lower()} and release.",
        ).pack(pady=5)

        self.start_x = None
        self.start_y = None
        self.rectangle = None

    def mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y

        if self.rectangle:
            self.canvas.delete(self.rectangle)

        self.rectangle = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="lime",
            width=3,
        )

    def mouse_move(self, event):
        if self.rectangle:
            self.canvas.coords(
                self.rectangle,
                self.start_x,
                self.start_y,
                event.x,
                event.y,
            )

    def mouse_up(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        x1 = int(x1 / self.scale)
        y1 = int(y1 / self.scale)
        x2 = int(x2 / self.scale)
        y2 = int(y2 / self.scale)

        width = x2 - x1
        height = y2 - y1

        if width < 5 or height < 5:
            return

        self.result = (x1, y1, width, height)

        core.log(
            f"{self.window.title()}: "
            f"X={x1}, Y={y1}, W={width}, H={height}"
        )

        self.window.destroy()


class Application:
    def __init__(self, root):
        state.ui = self

        self.root = root
        root.title("Sequential Minimap Route")
        root.geometry("500x550")
        root.resizable(False, False)
        
        synchronize_window_size()

        # ----------------------------------------------------
        # CONTROLS
        # ----------------------------------------------------

        controls = tk.Frame(root)
        controls.pack(pady=8)

        tk.Button(
            controls,
            text="Select Minimap",
            width=15,
            command=self.select_minimap,
        ).grid(row=0, column=0, padx=3)

        tk.Button(
            controls,
            text="Select Battlelist",
            width=15,
            command=self.select_battlelist,
        ).grid(row=0, column=1, padx=3)

        self.start_button = tk.Button(
            controls,
            text="START",
            width=10,
            bg="green",
            fg="white",
            command=self.start,
        )
        self.start_button.grid(row=0, column=2, padx=3)

        self.stop_button = tk.Button(
            controls,
            text="STOP",
            width=10,
            bg="red",
            fg="white",
            state="disabled",
            command=self.stop,
        )
        self.stop_button.grid(row=0, column=3, padx=3)

        tk.Button(
                    controls,
                    text="Select Backpack",
                    width=15,
                    command=self.select_backpack,
                ).grid(row=1, column=2, padx=3, pady=5)

        tk.Button(
            controls,
            text="Select Ring Slot",
            width=15,
            command=self.select_ring_slot,
        ).grid(row=1, column=3, padx=3, pady=5)

        self.ring_start_button = tk.Button(
            controls,
            text="START RING",
            width=13,
            command=self.start_ring,
        )
        self.ring_start_button.grid(row=2, column=0, padx=3, pady=5)

        self.ring_stop_button = tk.Button(
            controls,
            text="STOP RING",
            width=13,
            command=self.stop_ring,
        )
        self.ring_stop_button.grid(row=2, column=1, padx=3, pady=5)

        tk.Button(
            controls,
            text="Save Profile",
            width=13,
            command=self.save_profile,
        ).grid(row=1, column=0, padx=3, pady=5)

        tk.Button(
            controls,
            text="Load Profile",
            width=13,
            command=self.load_profile,
        ).grid(row=1, column=1, padx=3, pady=5)

        # ----------------------------------------------------
        # ROUTE
        # ----------------------------------------------------

        route_frame = tk.LabelFrame(root, text="Location Route")
        route_frame.pack(fill="x", padx=15, pady=6)

        list_frame = tk.Frame(route_frame)
        list_frame.pack(fill="x", padx=5, pady=5)

        self.location_list = tk.Listbox(
            list_frame,
            height=5,
        )
        self.location_list.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = tk.Scrollbar(
            list_frame,
            command=self.location_list.yview,
        )
        scrollbar.pack(side="right", fill="y")

        self.location_list.config(
            yscrollcommand=scrollbar.set,
        )

        buttons = tk.Frame(route_frame)
        buttons.pack(pady=4)

        tk.Button(
            buttons,
            text="Add Locations",
            width=15,
            command=self.add_locations,
        ).grid(row=0, column=0, padx=3)

        tk.Button(
            buttons,
            text="Move Up",
            width=10,
            command=self.move_up,
        ).grid(row=0, column=1, padx=3)

        tk.Button(
            buttons,
            text="Move Down",
            width=10,
            command=self.move_down,
        ).grid(row=0, column=2, padx=3)

        tk.Button(
            buttons,
            text="Remove",
            width=10,
            command=self.remove_location,
        ).grid(row=0, column=3, padx=3)

        tk.Button(
            buttons,
            text="Clear",
            width=10,
            command=self.clear_locations,
        ).grid(row=0, column=4, padx=3)

        self.route_label = tk.Label(
            route_frame,
            text="0 locations",
            fg="gray",
        )
        self.route_label.pack(pady=(0, 5))

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status_label = tk.Label(
            root,
            text="Status: stopped",
            font=("Arial", 12, "bold"),
        )
        self.status_label.pack(pady=4)

        # ----------------------------------------------------
        # REGION INFO
        # ----------------------------------------------------

        self.region_label = tk.Label(
            root,
            text=(
                "Minimap: not selected | "
                "Battlelist: not selected"
            ),
            fg="gray",
        )
        self.region_label.pack(pady=5)

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        log_frame = tk.LabelFrame(
            root,
            text=f"LOG - {config.LOG_FILE}",
        )
        log_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=8,
        )

        self.log_text = tk.Text(
            log_frame,
            height=12,
            width=105,
            bg="#111111",
            fg="#dddddd",
            insertbackground="white",
            font=("Consolas", 9),
            state="disabled",
        )
        self.log_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        log_scroll = tk.Scrollbar(
            log_frame,
            command=self.log_text.yview,
        )
        log_scroll.pack(side="right", fill="y")

        self.log_text.config(
            yscrollcommand=log_scroll.set,
        )

        tk.Button(
            root,
            text="Clear GUI Log",
            command=self.clear_gui_log,
        ).pack(pady=(0, 8))

    # ========================================================
    # GUI LOG
    # ========================================================

    def append_log(self, message):
        try:
            self.log_text.config(state="normal")

            timestamp = time.strftime("%H:%M:%S")

            self.log_text.insert(
                tk.END,
                f"[{timestamp}] {message}\n",
            )
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")

        except Exception:
            pass

    def clear_gui_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    # ========================================================
    # ADD LOCATION TEMPLATES
    # ========================================================

    def add_locations(self):
        filenames = filedialog.askopenfilenames(
            title="Select location templates in route order",
            filetypes=[
                (
                    "Image files",
                    "*.png *.jpg *.jpeg *.bmp",
                )
            ],
        )

        if not filenames:
            return

        for filename in filenames:
            image = cv2.imread(
                filename,
                cv2.IMREAD_COLOR,
            )

            if image is None:
                core.log(
                    f"Could not load: {filename}",
                    "warning",
                )
                continue

            name = filename.replace("\\", "/").split("/")[-1]

            state.location_templates.append(
                {
                    "file": filename,
                    "image": image,
                    "name": name,
                }
            )

            self.location_list.insert(
                tk.END,
                f"{len(state.location_templates)}. {name}",
            )

            core.log(f"Added route location: {name}")

        self.update_route_label()

    # ========================================================
    # MOVE UP
    # ========================================================

    def move_up(self):
        selection = self.location_list.curselection()

        if not selection:
            return

        index = selection[0]

        if index <= 0:
            return

        locations = state.location_templates
        locations[index - 1], locations[index] = (
            locations[index],
            locations[index - 1],
        )

        self.refresh_location_list()
        self.location_list.selection_set(index - 1)

    # ========================================================
    # MOVE DOWN
    # ========================================================

    def move_down(self):
        selection = self.location_list.curselection()

        if not selection:
            return

        index = selection[0]
        locations = state.location_templates

        if index >= len(locations) - 1:
            return

        locations[index + 1], locations[index] = (
            locations[index],
            locations[index + 1],
        )

        self.refresh_location_list()
        self.location_list.selection_set(index + 1)

    # ========================================================
    # REMOVE
    # ========================================================

    def remove_location(self):
        selection = self.location_list.curselection()

        if not selection:
            return

        del state.location_templates[selection[0]]
        self.reset_route_state()
        self.refresh_location_list()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_locations(self):
        state.location_templates.clear()
        self.reset_route_state()
        self.refresh_location_list()

    def reset_route_state(self):
        core.current_location_index = 0
        core.permanent_destination_index = None
        core.permanent_destination_template = None
        core.current_destination_match = None

    # ========================================================
    # REFRESH LIST
    # ========================================================

    def refresh_location_list(self):
        self.location_list.delete(0, tk.END)

        for i, location in enumerate(state.location_templates):
            self.location_list.insert(
                tk.END,
                f"{i + 1}. {location['name']}",
            )

        self.update_route_label()

    def update_route_label(self):
        self.route_label.config(
            text=f"{len(state.location_templates)} locations in route"
        )

    # ========================================================
    # SELECT MINIMAP
    # ========================================================

    def select_minimap(self):
        selector = RegionSelector(
            self.root,
            "Select Minimap"
        )

        self.root.wait_window(selector.window)

        if selector.result:
            state.minimap_region = selector.result
            self.update_region_text()

            core.log(
                f"Minimap selected: {state.minimap_region}"
            )
    # ========================================================
    # SELECT BATTLELIST
    # ========================================================

    def select_battlelist(self):
        selector = RegionSelector(
            self.root,
            "Select Battlelist"
        )

        self.root.wait_window(selector.window)

        if selector.result:
            state.battlelist_region = selector.result
            self.update_region_text()

            core.log(
                f"Battlelist selected: {state.battlelist_region}"
        )    # ========================================================
    
    def select_backpack(self):
        selector = RegionSelector(
            self.root,
            "Select Backpack Area",
        )

        self.root.wait_window(selector.window)

        if selector.result:
            state.backpack_slot_region = selector.result
            self.update_region_text()

            core.log(
                f"Backpack area selected: {state.backpack_slot_region}"
            )

    def select_ring_slot(self):
        selector = RegionSelector(
            self.root,
            "Select Ring Equipment Slot",
        )

        self.root.wait_window(selector.window)

        if selector.result:
            state.ring_equipment_region = selector.result
            self.update_region_text()

            core.log(
                f"Ring equipment slot selected: "
                f"{state.ring_equipment_region}"
            )
    # UPDATE REGION TEXT
    # ========================================================

    def update_region_text(self):
        def describe(name, region):
            if region:
                x, y, w, h = region
                return f"{name}: X={x} Y={y} W={w} H={h}"
            return f"{name}: not selected"

        regions = [
            describe("Minimap", state.minimap_region),
            describe("Battlelist", state.battlelist_region),
            describe("Backpack", state.backpack_slot_region),
            describe("Ring Slot", state.ring_equipment_region),
        ]

        self.region_label.config(
            text="\n".join(regions),
            justify="left",
            anchor="w",
        )
    
    def save_profile(self):
        if state.running:
            messagebox.showwarning(
                "Profile",
                "Stop the automation before saving a profile.",
            )
            return

        name = tk.simpledialog.askstring(
            "Save Profile",
            "Enter a profile name:",
            parent=self.root,
        )

        if not name or not name.strip():
            return

        try:
            path = profiles.save_profile(
                name=name,
                minimap_region=state.minimap_region,
                battlelist_region=state.battlelist_region,
                location_templates=state.location_templates,
            )

            core.log(f"Profile saved: {path}")

            messagebox.showinfo(
                "Profile Saved",
                f"Profile '{name.strip()}' saved successfully.",
            )

        except Exception as e:
            messagebox.showerror(
                "Save Profile Error",
                str(e),
            )

    def load_profile(self):
        if state.running:
            messagebox.showwarning(
                "Profile",
                "Stop the automation before loading a profile.",
            )
            return

        available = profiles.list_profiles()

        if not available:
            messagebox.showinfo(
                "Load Profile",
                "No saved profiles were found.",
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Load Profile")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Select a profile:",
        ).pack(padx=15, pady=(15, 5))

        selected = tk.StringVar(value=available[0])

        dropdown = tk.OptionMenu(
            dialog,
            selected,
            *available,
        )
        dropdown.pack(padx=15, pady=5)

        def confirm_load():
            name = selected.get()

            try:
                data = profiles.load_profile(name)

                # Validate and load all templates before changing state.
                new_locations = []

                for filename in data.get("locations", []):
                    image = cv2.imread(
                        filename,
                        cv2.IMREAD_COLOR,
                    )

                    if image is None:
                        raise ValueError(
                            f"Could not load location image:\n{filename}"
                        )

                    new_locations.append({
                        "file": filename,
                        "image": image,
                        "name": os.path.basename(filename),
                    })

                minimap = data.get("minimap_region")
                battlelist = data.get("battlelist_region")

                def valid_region(region):
                    return (
                        region is None
                        or (
                            isinstance(region, list)
                            and len(region) == 4
                            and all(
                                isinstance(v, int) and v >= 0
                                for v in region
                            )
                            and region[2] > 0
                            and region[3] > 0
                        )
                    )

                if not valid_region(minimap):
                    raise ValueError("Invalid minimap region in profile.")

                if not valid_region(battlelist):
                    raise ValueError("Invalid battlelist region in profile.")

                state.minimap_region = (
                    tuple(minimap) if minimap is not None else None
                )
                state.battlelist_region = (
                    tuple(battlelist) if battlelist is not None else None
                )
                state.location_templates = new_locations

                self.reset_route_state()
                self.refresh_location_list()
                self.update_region_text()

                core.log(f"Profile loaded: {name}")

                messagebox.showinfo(
                    "Profile Loaded",
                    f"Profile '{name}' loaded successfully.",
                )

                dialog.destroy()

            except Exception as e:
                messagebox.showerror(
                    "Load Profile Error",
                    str(e),
                    parent=dialog,
                )

        tk.Button(
            dialog,
            text="Load",
            command=confirm_load,
            width=12,
        ).pack(pady=5)

        tk.Button(
            dialog,
            text="Cancel",
            command=dialog.destroy,
            width=12,
        ).pack(pady=(0, 15))

    # ========================================================
    # START
    # ========================================================

    def start(self):
        if state.minimap_region is None:
            messagebox.showerror(
                "Minimap",
                "Select the minimap.",
            )
            return

        if state.battlelist_region is None:
            messagebox.showerror(
                "Battlelist",
                "Select the battlelist.",
            )
            return

        if not state.location_templates:
            messagebox.showerror(
                "Route",
                "Add at least one location.",
            )
            return

        try:
            first = windows.get_window(config.FIRST_WINDOW)
            second = windows.get_window(config.SECOND_WINDOW)

            first.resizeTo(second.width, second.height)
            time.sleep(0.5)

        except Exception as e:
            messagebox.showerror("Window error", str(e))
            return

        self.reset_route_state()

        if not core.set_permanent_destination(0):
            messagebox.showerror(
                "Route",
                "Could not establish the first destination.",
            )
            return

        state.running = True

        core.set_state(
            "FIND_LOCATION",
            "START pressed",
        )

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: starting")

        core.log("========================================")
        core.log("START BUTTON PRESSED")
        core.log("ROUTE:")

        for i, location in enumerate(state.location_templates):
            core.log(f"{i + 1}. {location['name']}")

        core.log("========================================")

        core.log(
            f"PERMANENT DESTINATION: "
            f"{state.permanent_destination_index + 1}. "
            f"{state.permanent_destination_template['name']}"
        )

        import threading

        thread = threading.Thread(
            target=core.automation_loop,
            daemon=True,
        )
        thread.start()

        self.root.after(100, core.update_visuals)

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):
        state.running = False

        core.set_state(
            "STOPPED",
            "STOP pressed",
        )

        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Status: stopped")

        core.log("AUTOMATION STOPPED")

#RING WORKER

    def start_ring(self):
        if state.ring_equipment_region is None:
            messagebox.showerror(
                "Ring manager",
                "Configure the ring equipment region first.",
            )
            return

        if state.backpack_slot_region is None:
            messagebox.showerror(
                "Ring manager",
                "Configure the backpack region first.",
            )
            return

        if workers.manager.start("RingManager", workers.ring_worker):
            core.log("Independent ring monitoring started")


    def stop_ring(self):
        workers.manager.stop("RingManager")
        core.log("Ring monitoring stop requested")

def main():
    root = tk.Tk()
    Application(root)
    root.mainloop()


if __name__ == "__main__":
    main()