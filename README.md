# System Info Viewer

System Info Viewer is a Python application built with Tkinter that provides an interactive graphical interface to view and manage system information. The application is designed for systems running on FreeBSD.

## Notes
    This is a work in progress.  I do not guarentee it's functionality or that it is safe to use.  Use at your own risk.
    In other words "it works on my machine".
    Some refactoring and bug fixes provided by AI.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features

- View detailed system information, including OS details, CPU information, GPU details, memory, and storage.
- Display a list of running processes with details such as CPU usage, memory usage, and status.
- Explore and uninstall installed applications using the graphical interface.
- Display and create ZFS snapshots for a selected ZFS pool.
- Manage Boot Environments (BE) by creating and listing them.

## Requirements

- Python 3.x
- Tkinter
- PIL (Python Imaging Library)
- psutil
- cpuinfo

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/system-info-viewer.git
    ```

2. Navigate to the project directory:

    ```bash
    cd system-info-viewer
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the application using the following command:

```bash
sudo python system_info_viewer.py
```

System Tab
  Displays system information.  Note: Currently will not display GPU information.  This is a work in progress to find a suitable way to do this.

Processes Tab
  Displays running processes and allows the user to kill processes by either typing the PID into the textbox or selecting it from the list.

Settings Tab
  Displays various settings, provided in the "./resources/settings.json" file, and allows them to be quickly run by pressing the run button or modifying the command before running by typing in the text box.
  Output from the command will be displayed in the output box for each command.

Applications Tab
  Displays a list of all installed applications and allows the user to uninstall an application by either selecting it from the list or typing it's name into the text box.

ZFS Snapshots Tab
  Displays the ZFS snapshots for the selected ZFS pool by choosing it from the drop down and pressing the show button.
  Snapshots can be created by pressing the Create Snapshot button.  Snapshots can be named by entering a name in the Snapshots Name textbox.  The name of the snapshot defaults to the current date and time.

Boot Environments Tab
  Displays the boot environments by pressing the show button.
  Boot environments can be created by pressing the Create Boot Environment button.  Boot Environments can be named by entering a name in the Boot Environments Name textbox.  The name of the snapshot defaults to the current date and time.

Logs Tab
  Displays the syslog or dmesg logs in a scrollable window.

Contributing

Contributions are welcome! Feel free to open issues or pull requests.

License

This project is licensed under the MIT License - see the LICENSE file for details.
