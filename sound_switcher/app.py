"""GTK application for switching audio output devices."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # type: ignore

from . import backend


class SoundSwitcherWindow(Gtk.Window):
    """Main window that lists sinks and allows switching/volume control."""

    def __init__(self) -> None:
        super().__init__(title="Sound Output Switcher")
        self.set_border_width(12)
        self.set_default_size(360, 180)
        self.set_resizable(False)

        self._sinks = []
        self._current_sink_name: str | None = None

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer_box.set_margin_top(12)
        outer_box.set_margin_bottom(12)
        outer_box.set_margin_start(12)
        outer_box.set_margin_end(12)
        self.add(outer_box)

        label = Gtk.Label(label="Output Device")
        label.set_halign(Gtk.Align.START)
        outer_box.pack_start(label, False, False, 0)

        self.combo = Gtk.ComboBoxText()
        self.combo.connect("changed", self.on_device_changed)
        outer_box.pack_start(self.combo, False, False, 0)

        volume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer_box.pack_start(volume_box, False, False, 0)

        vol_label = Gtk.Label(label="Volume")
        vol_label.set_halign(Gtk.Align.START)
        volume_box.pack_start(vol_label, False, False, 0)

        self.volume_adjustment = Gtk.Adjustment(value=0, lower=0, upper=150, step_increment=1, page_increment=10)
        self.volume_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.volume_adjustment)
        self.volume_slider.set_digits(0)
        self.volume_slider.set_value_pos(Gtk.PositionType.RIGHT)
        self.volume_slider.connect("value-changed", self.on_volume_changed)
        volume_box.pack_start(self.volume_slider, True, True, 0)

        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        outer_box.pack_start(self.status_label, False, False, 0)

        refresh_button = Gtk.Button(label="Refresh Devices")
        refresh_button.connect("clicked", lambda _button: self.refresh_devices())
        outer_box.pack_end(refresh_button, False, False, 0)

        self.refresh_devices()

    def refresh_devices(self) -> None:
        try:
            sinks = backend.list_sinks()
        except backend.PactlError as exc:
            self.set_status(str(exc), error=True)
            return

        self.combo.handler_block_by_func(self.on_device_changed)
        self.volume_slider.handler_block_by_func(self.on_volume_changed)
        self.combo.remove_all()
        self._current_sink_name = None
        self._sinks = sinks
        for sink in sinks:
            self.combo.append(sink.name, sink.description)
            if sink.is_default:
                self.combo.set_active_id(sink.name)
                self.volume_slider.set_value(sink.volume_percent)
                self._current_sink_name = sink.name

        if sinks and self.combo.get_active() == -1:
            first_sink = sinks[0]
            self.combo.set_active_id(first_sink.name)
            self.volume_slider.set_value(first_sink.volume_percent)
            self._current_sink_name = first_sink.name

        self.volume_slider.handler_unblock_by_func(self.on_volume_changed)
        self.combo.handler_unblock_by_func(self.on_device_changed)

        if not sinks:
            self.set_status("No audio sinks available.", error=True)
            self.volume_slider.set_sensitive(False)
            return

        self.volume_slider.set_sensitive(True)
        self.set_status("Loaded audio devices.")

    def on_device_changed(self, combo: Gtk.ComboBoxText) -> None:
        sink_name = combo.get_active_id()
        if not sink_name:
            return
        try:
            backend.set_default_sink(sink_name)
        except backend.PactlError as exc:
            self.set_status(str(exc), error=True)
            return

        self._current_sink_name = sink_name
        try:
            volume = backend.get_sink_volume(sink_name)
        except backend.PactlError as exc:
            self.set_status(str(exc), error=True)
        else:
            self.volume_slider.handler_block_by_func(self.on_volume_changed)
            self.volume_slider.set_value(volume)
            self.volume_slider.handler_unblock_by_func(self.on_volume_changed)
            self.set_status(f"Switched to {combo.get_active_text()}.")

    def on_volume_changed(self, slider: Gtk.Scale) -> None:
        if self._current_sink_name is None:
            return
        value = slider.get_value()
        try:
            backend.set_sink_volume(self._current_sink_name, value)
        except backend.PactlError as exc:
            self.set_status(str(exc), error=True)
        else:
            self.set_status(f"Volume set to {value:.0f}%.")

    def set_status(self, message: str, error: bool = False) -> None:
        markup = GLib.markup_escape_text(message)
        if error:
            markup = f"<span foreground='red'>{markup}</span>"
        self.status_label.set_markup(markup)


def run() -> None:
    """Entry point to run the GTK application."""
    win = SoundSwitcherWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
