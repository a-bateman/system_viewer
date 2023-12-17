import tkinter as tk
from tkinter import ttk, simpledialog, scrolledtext, messagebox
import platform
import subprocess
import psutil
from PIL import Image, ImageTk
import cpuinfo
import json
import csv
from datetime import datetime
import os
import re

class SystemInfo:
    def __init__(self):
        if os.geteuid() != 0:
            print("This application must be run as root.")
            exit()
        self.root = tk.Tk()
        self.root.title("System View")

        self.settings_data = self.read_settings_from_json("./resources/settings.json")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both')

        self.create_tab("System", self.create_system_tab_content)
        self.create_tab("Processes", self.create_processes_tab_content, self.schedule_update_processes)
        self.create_tab("Settings", self.create_settings_tab_content)
        self.create_tab("Applications", self.create_applications_tab_content)
        self.create_tab("ZFS Snapshots", self.create_zfs_snapshots_tab_content)
        self.create_tab("Boot Environments", self.create_boot_environments_tab_content)
        self.create_tab("Logs", self.create_logs_tab_content)

        self.app_description_var = tk.StringVar()

    def get_log_file_name(self):
        current_date = datetime.now()
        return current_date.strftime('%d%m%Y') + ".csv"

    def create_tab(self, text, content_func, update_func=None, **kwargs):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=text)
        content_func(tab, **kwargs)
        if update_func:
            tab.bind("<Visibility>", lambda event, update_func=update_func: self.on_tab_visibility(tab, update_func))

    def create_logs_tab_content(self, parent):
        logs_frame = ttk.Frame(parent)
        logs_frame.pack(expand=True, fill='both')

        log_label = ttk.Label(logs_frame, text="Logs:")
        log_label.pack(pady=5)

        # Create a frame to hold the buttons
        buttons_frame = ttk.Frame(logs_frame)
        buttons_frame.pack(pady=5)

        # Button to display syslog
        syslog_button = ttk.Button(buttons_frame, text="Show Syslog", command=self.show_syslog)
        syslog_button.pack(side=tk.LEFT, padx=5)

        # Button to display dmesg
        dmesg_button = ttk.Button(buttons_frame, text="Show dmesg", command=self.show_dmesg)
        dmesg_button.pack(side=tk.LEFT, padx=5)

        # Create a scrolled text widget for displaying logs
        self.log_scrolled_text = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD)
        self.log_scrolled_text.pack(expand=True, fill='both', padx=10, pady=10)

    # Add these methods to handle button clicks
    def show_syslog(self):
        syslog_output = subprocess.run(['cat', '/var/log/messages'], capture_output=True, text=True)
        self.log_scrolled_text.config(state=tk.NORMAL)
        self.log_scrolled_text.delete(1.0, tk.END)
        self.log_scrolled_text.insert(tk.END, syslog_output.stdout)
        self.log_scrolled_text.config(state=tk.DISABLED)

    def show_dmesg(self):
        dmesg_output = subprocess.run(['dmesg'], capture_output=True, text=True)
        self.log_scrolled_text.config(state=tk.NORMAL)
        self.log_scrolled_text.delete(1.0, tk.END)
        self.log_scrolled_text.insert(tk.END, dmesg_output.stdout)
        self.log_scrolled_text.config(state=tk.DISABLED)


    #If the tab is visible then update what is displayed.
    def on_tab_visibility(self, tab, update_func):
        if tab.winfo_ismapped():
            update_func()

    def create_system_tab_content(self, parent):
        system_info = self.compile_system_information_list()
        system_frame = ttk.Frame(parent)
        system_frame.pack(expand=True, fill='both')

        image_label = self.get_system_image()
        image_label.pack(pady=10)

        tree = self.create_treeview(system_frame, ('Property', 'Value'))
        self.populate_treeview(tree, system_info)
        tree.pack(expand=True, fill='both', padx=10, pady=10)

    def create_settings_tab_content(self, parent):
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(expand=True, fill='both')

        scroll_view = ttk.Frame(settings_frame)
        scroll_view.pack(expand=True, fill='both', padx=10, pady=10)

        for setting in self.settings_data:
            box = self.create_setting_box(setting, scroll_view)
            box.pack(pady=5)

    def create_applications_tab_content(self, parent):
        applications_frame = ttk.Frame(parent)
        applications_frame.pack(expand=True, fill='both')

        applications_label = ttk.Label(applications_frame, text="Installed Applications:")
        applications_label.pack(pady=5)

        self.applications_listbox = tk.Listbox(applications_frame, selectmode=tk.SINGLE)
        self.applications_listbox.pack(expand=True, fill='both', pady=10)

        app_name_var = tk.StringVar()
        app_name_entry_label = ttk.Label(applications_frame, text="Selected Application:")
        app_name_entry_label.pack(pady=5)

        app_name_entry = ttk.Entry(applications_frame, textvariable=app_name_var)
        app_name_entry.pack(pady=5)

        uninstall_button = ttk.Button(applications_frame, text="Uninstall Application", command=lambda: self.handle_uninstall_button(app_name_var))
        uninstall_button.pack(pady=5)

        self.applications_listbox.bind('<<ListboxSelect>>', lambda event, app_name_var=app_name_var: self.handle_app_selection(app_name_var))

        installed_apps = self.get_installed_applications_with_description()
        self.update_applications_listbox_data(installed_apps)


    def handle_uninstall_button(self, app_name_var):
        app_name = app_name_var.get()
        if not app_name:
            messagebox.showwarning("Error", "Please select an application to uninstall.")
            return

        # Confirm uninstallation
        confirmation = messagebox.askyesno("Confirm Uninstall", f"Are you sure you want to uninstall {app_name}?")
        if not confirmation:
            return

        # Call uninstall_application with the actual app_name, not the app_name_var
        self.uninstall_application(app_name)

    def handle_app_selection(self, app_name_var):
        selected_index = self.applications_listbox.curselection()
        if selected_index:
            app_info = self.applications_listbox.get(selected_index)
            app_name, app_description = self.parse_app_info(app_info)
            app_name_var.set(app_name)
            self.app_description_var.set(app_description)

#Get information about the hardware, if available.  Will put "not available" if it cannot get the info.
    def compile_system_information_list(self):
        system_info = []

        os_info = [('Operating System', platform.system()), ('OS Version', platform.version())]
        system_info.extend(os_info)

        cpu_info = [('CPU Name', cpuinfo.get_cpu_info()['brand_raw']),
                    ('CPU Core Count', psutil.cpu_count(logical=False)),
                    ('CPU Speed', f"{psutil.cpu_freq().current} MHz")]
        system_info.extend(cpu_info)

        gpu_name, gpu_driver, vram = self.get_freebsd_gpu_info()
        if gpu_name is not None:
            gpu_info = [('GPU Name', gpu_name), ('GPU Driver', gpu_driver), ('VRAM', vram)]
            system_info.extend(gpu_info)
        else:
            system_info.append(('GPU Information', 'Not available'))

        mem = psutil.virtual_memory()
        memory_info = [('Available RAM', f"{mem.available / (1024 ** 3):.2f} GB")]
        system_info.extend(memory_info)

        root_partition = psutil.disk_usage('/')
        storage_info = [('Hard Drive Name', '/'), ('Total Space', f"{root_partition.total / (1024 ** 3):.2f} GB"),
                        ('Used Space', f"{root_partition.used / (1024 ** 3):.2f} GB"),
                        ('Free Space', f"{(root_partition.total - root_partition.used) / (1024 ** 3):.2f} GB")]
        system_info.extend(storage_info)

        # Run ifconfig and extract interface and IP address
        ifconfig_output = subprocess.run(['ifconfig'], capture_output=True, text=True, check=True)
        for line in ifconfig_output.stdout.split('\n'):
            if line and line.split()[0][-1] == ':' and (line.startswith('wlan') or line.startswith('em')):
                iface = line.split()[0]
            elif 'inet ' in line:
                ip_address = line.split()[1]
                system_info.append((iface, ip_address))

        return system_info

#Get the image to display at the bottom of the screen.  Modify this to any image you'd like.
    def get_system_image(self):
        original_image = Image.open("./resources/system_image.jpg")
        resized_image = original_image.resize((150, 150), Image.BICUBIC)
        tk_image = ImageTk.PhotoImage(resized_image)
        image_label = tk.Label(self.root, image=tk_image, anchor='center')
        image_label.image = tk_image
        return image_label

    def get_freebsd_gpu_info(self):
        try:
            # Run pciconf to get PCI device information
            result = subprocess.run(['pciconf', '-lv'], capture_output=True, text=True, check=True)

            # Search for the GPU information in the output
            gpu_name, gpu_driver, vram = None, None, None
            for line in result.stdout.split('\n'):
                if 'vgapci' in line.lower():
                    # Extract GPU information (you might need to adjust this based on your output format)
                    match = re.search(r'Device: (.+?),', line)
                    gpu_name = match.group(1).strip() if match else None

                    match = re.search(r'driver: (.+)', line)
                    gpu_driver = match.group(1).strip() if match else None

                    match = re.search(r'Memory: (.+)', line)
                    vram = match.group(1).strip() if match else None

                    break

            return gpu_name, gpu_driver, vram

        except subprocess.CalledProcessError as e:
            print(f"Error running pciconf command: {e}")
            return None, None, None
        except Exception as e:
            print(f"Error: {e}")
            return None, None, None

#Use pkg info to get the names of installed applications
    def get_installed_applications_with_description(self):
        try:
            result = subprocess.run(["pkg", "info"], capture_output=True, text=True)
            installed_apps_info = result.stdout.splitlines()
            return [self.parse_app_info(app_info) for app_info in installed_apps_info]
        except Exception as e:
            print(f"Error getting installed applications: {e}")
            return []

    def parse_app_info(self, app_info):
        parts = app_info.split(' ', 1)
        name_version = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        app_name = re.sub(r'[-._](\d+)', '', name_version)
        return app_name.strip(), description

    def update_applications_treeview_data(self, data):
        for item in self.applications_treeview.get_children():
            self.applications_treeview.delete(item)
        for item in data:
            self.applications_treeview.insert("", "end", values=item)


    def update_applications_listbox_data(self, data):
        self.applications_listbox.delete(0, tk.END)
        for name_version, description in data:
            self.applications_listbox.insert(tk.END, name_version)

    def uninstall_application(self, app_name):
        try:
            uninstall_command = f"pkg delete -y {app_name}"
            subprocess.run(uninstall_command, shell=True, text=True, check=True,)
            installed_apps = self.get_installed_applications_with_description()
            self.update_applications_listbox_data(installed_apps)
        except subprocess.CalledProcessError as e:
            print(f"Error uninstalling application: {e}")
        except Exception as e:
            print(f"Error uninstalling application: {e}")

    def create_treeview(self, parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        for col in columns:
            tree.heading(col, text=col)
        return tree  # Return the created tree object

    def populate_treeview(self, tree, data):
        for item in data:
            tree.insert("", "end", values=item)

    def create_setting_box(self, setting, parent):
        def update_entry_height():
            entry_lines = int(entry_command.index('end-1c').split('.')[0])
            entry_command.config(height=entry_lines)

        box = ttk.Frame(parent)

        label_name = ttk.Label(box, text=setting["name"])
        label_name.grid(row=0, column=0, sticky='w')

        label_description = ttk.Label(box, text=setting["description"])
        label_description.grid(row=1, column=0, sticky='w')

        command_var = tk.StringVar(value=setting["command"])
        entry_command = tk.Text(box, wrap=tk.WORD)
        entry_command.insert(tk.END, command_var.get())
        entry_command.grid(row=2, column=0, sticky='w')

        output_text = scrolledtext.ScrolledText(box, height=4, wrap=tk.WORD)
        output_text.grid(row=3, column=0, sticky='w')

        btn_run = ttk.Button(box, text="Run", command=lambda: self.run_command(setting, entry_command, output_text))
        btn_run.grid(row=4, column=0, pady=5)

        box.after(100, update_entry_height)

        return box

    def run_command(self, setting, command_var, output_text):
        modified_command = command_var.get()

        requires_sudo = any(keyword in modified_command.lower() for keyword in ['pkg', 'delete', 'install'])

        if requires_sudo and not modified_command.strip().lower().startswith('sudo '):
            modified_command = f'sudo {modified_command}'

        try:
            result = subprocess.run(modified_command, shell=True, capture_output=True, text=True)
            output = result.stdout
            if result.returncode != 0:
                output += "\nError: " + result.stderr
        except Exception as e:
            output = f"Error: {e}"

        setting["command"] = modified_command

        with open("settings.json", 'w') as file:
            json.dump(self.settings_data, file, indent=2)

        output_text.config(state=tk.NORMAL)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, output)
        output_text.config(state=tk.DISABLED)

    def schedule_update_processes(self):
        self.update_processes_data()
        self.root.after(2000, self.schedule_update_processes)

    def update_processes_treeview_data(self, data):
        for item in self.processes_treeview.get_children():
            self.processes_treeview.delete(item)
        for item in data:
            self.processes_treeview.insert("", "end", values=item)

    def update_process_treeview_data(self, data):
        for item in self.processes_treeview.get_children():
            self.processes_treeview.delete(item)
        for item in data:
            self.processes_treeview.insert("", "end", values=item)

    def update_processes_data(self):
        processes = []

        for process in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            process_info = (process.info['name'], process.info['pid'],
                            f"{process.info['cpu_percent']:.2f}", f"{process.info['memory_percent']:.2f}",
                            process.info['status'])
            processes.append(process_info)

        processes.sort(key=lambda x: int(x[1]))

        self.update_processes_treeview_data(processes)

    def kill_process(self):
        try:
            pid_str = self.pid_entry.get()
            if pid_str:
                pid = int(pid_str)
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=5)
                print(f"Process with PID {pid} terminated.")
            else:
                print("Error killing process: PID is empty.")
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(f"Error killing process: {e}")

    def terminate_process(self):
        try:
            pid = int(self.pid_entry.get())
            os.system(f"kill -TERM {pid}")
            print(f"Process with PID {pid} terminated.")
        except (ValueError, OSError) as e:
            print(f"Error killing process: {e}")

    def read_settings_from_json(self, filename):
        try:
            with open(filename, 'r') as file:
                settings_data = json.load(file)
                if isinstance(settings_data, dict):
                    settings_data = [settings_data]
                return settings_data
        except FileNotFoundError:
            print(f"Error: {filename} not found.")
            return []

    def create_processes_tab_content(self, parent):
        processes_frame = ttk.Frame(parent)
        processes_frame.pack(expand=True, fill='both')

        processes_label = ttk.Label(processes_frame, text="Processes Information:")
        processes_label.pack(pady=5)

        self.processes_treeview = self.create_treeview(processes_frame, ('Name', 'PID', 'CPU %', 'Memory %', 'Status'))
        self.update_processes_data()
        self.processes_treeview.pack(expand=True, fill='both', padx=10, pady=10)

        kill_frame = ttk.Frame(processes_frame)
        kill_frame.pack(expand=True, fill='both', pady=10)

        kill_label = ttk.Label(kill_frame, text="Enter PID to terminate a process:")
        kill_label.pack(pady=5)

        self.pid_entry = ttk.Entry(kill_frame)
        self.pid_entry.pack(pady=5)

        kill_button = ttk.Button(kill_frame, text="Kill Process (forceful)", command=self.kill_process)
        kill_button.pack(pady=5)

        terminate_button = ttk.Button(kill_frame, text="Terminate Process (graceful)", command=self.terminate_process)
        terminate_button.pack(pady=5)

        # Bind the click event to the update_pid_entry function
        self.processes_treeview.bind('<ButtonRelease-1>', self.update_pid_entry)

    def update_pid_entry(self, event):
        selected_item = self.processes_treeview.selection()
        if selected_item:
            pid = self.processes_treeview.item(selected_item, 'values')[1]
            self.pid_entry.delete(0, tk.END)
            self.pid_entry.insert(0, pid)

    def create_zfs_snapshots_tab_content(self, parent):
        zfs_snapshots_frame = ttk.Frame(parent)
        zfs_snapshots_frame.pack(expand=True, fill='both')

        zfs_snapshots_label = ttk.Label(zfs_snapshots_frame, text="ZFS Snapshots:")
        zfs_snapshots_label.pack(pady=5)

        # Dropdown menu to select ZFS pool
        zfs_pool_label = ttk.Label(zfs_snapshots_frame, text="Select ZFS Pool:")
        zfs_pool_label.pack(pady=5)

        # Get the list of ZFS pools
        zfs_pools = self.get_zfs_pools()
        zfs_pool_var = tk.StringVar(value=zfs_pools[0] if zfs_pools else '')
        zfs_pool_dropdown = ttk.Combobox(zfs_snapshots_frame, textvariable=zfs_pool_var, values=zfs_pools)
        zfs_pool_dropdown.pack(pady=5)

        # Entry widget for the user to input the ZFS snapshot name
        snapshot_name_label = ttk.Label(zfs_snapshots_frame, text="Snapshot Name:")
        snapshot_name_label.pack(pady=5)

        snapshot_name_var = tk.StringVar()
        snapshot_name_entry = ttk.Entry(zfs_snapshots_frame, textvariable=snapshot_name_var)
        snapshot_name_entry.pack(pady=5)

        # Button to display ZFS snapshots
        show_snapshots_button = ttk.Button(zfs_snapshots_frame, text="Show ZFS Snapshots", command=lambda: self.show_zfs_snapshots(self.zfs_snapshots_treeview, zfs_pool_var.get()))
        show_snapshots_button.pack(side=tk.LEFT, padx=5)

        # Button to create ZFS snapshot
        create_snapshot_button = ttk.Button(zfs_snapshots_frame, text="Create ZFS Snapshot", command=lambda: self.create_zfs_snapshot(zfs_pool_var.get(), snapshot_name_var.get()))
        create_snapshot_button.pack(side=tk.LEFT, padx=5)

        # Treeview to display ZFS snapshots
        columns = ('Snapshot Name', 'Creation Time')
        self.zfs_snapshots_treeview = self.create_treeview(zfs_snapshots_frame, columns)
        self.zfs_snapshots_treeview.pack(expand=True, fill='both', padx=10, pady=10)

        # Bind the selection event to update the selected ZFS pool
        zfs_pool_dropdown.bind("<<ComboboxSelected>>", lambda event, tree=self.zfs_snapshots_treeview, zfs_pool_var=zfs_pool_var: self.show_zfs_snapshots(tree, zfs_pool_var.get()))


    def show_zfs_snapshots(self, tree, zfs_pool):
        try:
            # Run the zfs list command to display ZFS snapshots for the selected pool
            result = subprocess.run(['zfs', 'list', '-t', 'snapshot', '-o', 'name,creation', '-r', zfs_pool], capture_output=True, text=True, check=True)
            snapshots = [line.split('\t') for line in result.stdout.splitlines()]
            # Remove header
            snapshots = snapshots[1:]

            # Clear existing items in the Treeview
            for item in tree.get_children():
                tree.delete(item)

            # Populate Treeview with ZFS snapshots
            for snapshot in snapshots:
                tree.insert("", "end", values=snapshot)

        except subprocess.CalledProcessError as e:
            print(f"Error running 'zfs list' command: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def create_zfs_snapshot(self, zfs_pool, snapshot_name):
        try:
            # Use the provided snapshot name or generate one based on the current date and time
            snapshot_name = snapshot_name or f'{zfs_pool}@{datetime.now().strftime("%Y%m%d_%H%M%S")}'

            # Run the zfs snapshot command to create a ZFS snapshot for the selected pool
            subprocess.run(['zfs', 'snapshot', snapshot_name], check=True)
            print(f"ZFS snapshot '{snapshot_name}' created successfully.")

            # Refresh ZFS snapshots in the Treeview
            self.show_zfs_snapshots(self.zfs_snapshots_treeview, zfs_pool)

        except subprocess.CalledProcessError as e:
            print(f"Error running 'zfs snapshot' command: {e}")
        except Exception as e:
            print(f"Error: {e}")


    def get_zfs_pools(self):
        try:
            result = subprocess.run(['zpool', 'list', '-H', '-o', 'name'], capture_output=True, text=True, check=True)
            return result.stdout.splitlines()
        except subprocess.CalledProcessError as e:
            print(f"Error getting ZFS pools: {e}")
            return []

    def show_boot_environments(self):
        try:
            # Run the beadm list command to display boot environments
            result = subprocess.run(['beadm', 'list'], capture_output=True, text=True, check=True)
            boot_env_output = result.stdout

            # Display the boot environments in the Treeview
            self.update_boot_environments_treeview(boot_env_output)
        except subprocess.CalledProcessError as e:
            print(f"Error running 'beadm list' command: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def update_boot_environments_treeview(self, boot_env_output):
        try:
            # Clear existing items in the Treeview
            for item in self.boot_environments_treeview.get_children():
                self.boot_environments_treeview.delete(item)

            # Populate Treeview with boot environments
            boot_environments = [line.strip() for line in boot_env_output.splitlines()]
            for boot_env in boot_environments:
                self.boot_environments_treeview.insert("", "end", values=(boot_env,))
        except Exception as e:
            print(f"Error updating boot environments Treeview: {e}")

    def update_boot_env_entry(self, event):
        selected_item = self.boot_environments_treeview.selection()
        if selected_item:
            boot_env = self.boot_environments_treeview.item(selected_item, 'values')[0]
            # Update your entry or do anything you want with the selected boot environment
            print(f"Selected Boot Environment: {boot_env}")

    def create_boot_environments_tab_content(self, parent):
        boot_environments_frame = ttk.Frame(parent)
        boot_environments_frame.pack(expand=True, fill='both')

        boot_environments_label = ttk.Label(boot_environments_frame, text="Boot Environments:")
        boot_environments_label.pack(pady=5)

        # Entry widget for the user to input the boot environment name
        be_name_label = ttk.Label(boot_environments_frame, text="Boot Environment Name:")
        be_name_label.pack(pady=5)

        be_name_var = tk.StringVar()
        be_name_entry = ttk.Entry(boot_environments_frame, textvariable=be_name_var)
        be_name_entry.pack(pady=5)

        # Button to show boot environments
        show_boot_env_button = ttk.Button(boot_environments_frame, text="Show Boot Environments", command=self.show_boot_environments)
        show_boot_env_button.pack(side=tk.LEFT, padx=5)

        # Button to create boot environment
        create_boot_env_button = ttk.Button(boot_environments_frame, text="Create Boot Environment", command=lambda: self.create_boot_environment(be_name_var.get()))
        create_boot_env_button.pack(side=tk.LEFT, padx=5)

        # Treeview to display boot environments
        columns = ('Boot Environment',)
        self.boot_environments_treeview = self.create_treeview(boot_environments_frame, columns)
        self.boot_environments_treeview.pack(expand=True, fill='both', padx=10, pady=10)

        # Bind the selection event to update the selected boot environment
        self.boot_environments_treeview.bind('<ButtonRelease-1>', self.update_boot_env_entry)

        # Store the Boot Environments Treeview as an instance variable
        self.boot_environments_treeview_instance = self.boot_environments_treeview

    def create_boot_environment(self, be_name):
        try:
            # Use the provided boot environment name or generate one based on the current date and time
            new_be_name = be_name or 'be_' + datetime.now().strftime('%Y%m%d_%H%M%S')

            # Run the beadm create command to create a new boot environment
            subprocess.run(['beadm', 'create', new_be_name], check=True)
            print(f"Boot environment '{new_be_name}' created successfully.")

            # Refresh the Boot Environments Treeview after creating a new boot environment
            self.show_boot_environments()
        except subprocess.CalledProcessError as e:
            print(f"Error running 'beadm create' command: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def mainloop(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SystemInfo()
    app.mainloop()
