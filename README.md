# Linux Audio Output Device Switcher

A simple GTK-based desktop application for Linux that allows you to quickly switch between available audio output devices and adjust their volume. The app uses `pactl` to interact with PulseAudio/PipeWire.

## Requirements

- Python 3.9+
- PyGObject (`python3-gi` package)
- PulseAudio or PipeWire with `pactl`

On Debian/Ubuntu-based distributions you can install the dependencies with:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 pulseaudio-utils
```

## Running the application

Clone this repository and run:

```bash
python3 main.py
```

The window displays the available sinks. Selecting a different sink will set it as the system default, and moving the slider adjusts its volume.
