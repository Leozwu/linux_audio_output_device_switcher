"""Utilities for interacting with PulseAudio/PipeWire via pactl."""
from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
from typing import List


@dataclass
class AudioSink:
    """Represents an audio sink/output device."""

    name: str
    description: str
    is_default: bool
    volume_percent: float


class PactlError(RuntimeError):
    """Raised when pactl commands fail."""


_VOLUME_PATTERN = re.compile(r"/\s*(?P<percent>\d+)%")


def _run_pactl_command(*args: str) -> str:
    """Run a pactl command and return its output."""
    try:
        result = subprocess.run(
            ["pactl", *args],
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - environment specific
        raise PactlError("pactl command not found. Install PulseAudio utilities.") from exc
    except subprocess.CalledProcessError as exc:
        raise PactlError(exc.stderr.strip() or exc.stdout.strip()) from exc
    return result.stdout


def _collect_sink_details() -> List[dict[str, object]]:
    raw = _run_pactl_command("list", "sinks")
    sinks: List[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("Sink #"):
            if current.get("name"):
                sinks.append(current)
            current = {}
        elif stripped.startswith("Name: "):
            current["name"] = stripped.partition(": ")[-1]
        elif stripped.startswith("Description: "):
            current["description"] = stripped.partition(": ")[-1]
        elif stripped.startswith("Volume: "):
            match = _VOLUME_PATTERN.search(stripped)
            if match:
                current["volume"] = float(match.group("percent"))
    if current.get("name"):
        sinks.append(current)
    return sinks


def list_sinks() -> List[AudioSink]:
    """Return a list of available audio sinks."""
    default_sink_name = get_default_sink()
    sinks: List[AudioSink] = []
    for data in _collect_sink_details():
        name = str(data.get("name", ""))
        description = str(data.get("description", name))
        volume = float(data.get("volume", 0.0))
        sinks.append(
            AudioSink(
                name=name,
                description=description,
                is_default=name == default_sink_name,
                volume_percent=volume,
            )
        )
    return sinks


def get_default_sink() -> str:
    """Return the default sink name."""
    info = _run_pactl_command("info")
    for line in info.splitlines():
        if line.startswith("Default Sink: "):
            return line.partition(": ")[-1].strip()
    return ""


def get_sink_volume(sink_name: str) -> float:
    """Return the volume percentage for the provided sink."""
    for data in _collect_sink_details():
        name = str(data.get("name", ""))
        if name == sink_name:
            return float(data.get("volume", 0.0))
    raise PactlError(f"Unable to determine volume for sink '{sink_name}'.")


def set_default_sink(sink_name: str) -> None:
    """Set the default sink."""
    _run_pactl_command("set-default-sink", sink_name)


def set_sink_volume(sink_name: str, percent: float) -> None:
    """Set the volume percentage for the sink."""
    percent = max(0.0, min(percent, 150.0))
    volume_arg = f"{percent:.0f}%"
    _run_pactl_command("set-sink-volume", sink_name, volume_arg)
