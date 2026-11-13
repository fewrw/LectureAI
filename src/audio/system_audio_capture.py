
import queue
import threading
import time
from dataclasses import dataclass

import pyaudiowpatch as pyaudio


@dataclass
class AudioChunk:
    data: bytes
    captured_at: float
    sample_rate: int
    channels: int


class SystemAudioCapture:
    def __init__(self, queue_size=600):
        self._audio = None
        self._stream = None

        self._stop_event = threading.Event()
        self._chunks = queue.Queue(maxsize=queue_size)

        self._lock = threading.Lock()

        self._running = False
        self._last_error = None
        self._device_name = None

        self.sample_rate = None
        self.channels = None
        self.dropped_chunks = 0

    @property
    def is_running(self):
        return self._running

    @property
    def last_error(self):
        return self._last_error

    @property
    def device_name(self):
        return self._device_name

    @staticmethod
    def list_output_devices():
        audio = pyaudio.PyAudio()

        try:
            wasapi = audio.get_host_api_info_by_type(
                pyaudio.paWASAPI
            )

            wasapi_index = wasapi["index"]
            default_index = wasapi["defaultOutputDevice"]

            loopbacks = list(
                audio.get_loopback_device_info_generator()
            )

            devices = []

            for index in range(audio.get_device_count()):
                device = audio.get_device_info_by_index(index)

                if device["hostApi"] != wasapi_index:
                    continue

                if device["maxOutputChannels"] < 1:
                    continue

                output_name = device["name"]
                loopback = None

                for candidate in loopbacks:
                    loopback_name = candidate["name"].removesuffix(
                        " [Loopback]"
                    )

                    if loopback_name.casefold() == output_name.casefold():
                        loopback = candidate
                        break

                devices.append({
                    "index": device["index"],
                    "name": output_name,
                    "is_default": device["index"] == default_index,
                    "loopback_available": loopback is not None,
                    "loopback_index": (
                        loopback["index"] if loopback else None
                    ),
                    "sample_rate": (
                        int(loopback["defaultSampleRate"])
                        if loopback else None
                    ),
                    "channels": (
                        int(loopback["maxInputChannels"])
                        if loopback else None
                    ),
                })

            return devices

        finally:
            audio.terminate()

    def _find_loopback_device(self, audio, output_device_index=None):
        wasapi = audio.get_host_api_info_by_type(
            pyaudio.paWASAPI
        )

        if output_device_index is None:
            output_device_index = wasapi["defaultOutputDevice"]

        output = audio.get_device_info_by_index(
            output_device_index
        )

        if output["hostApi"] != wasapi["index"]:
            raise RuntimeError(
                "Выбранное устройство не относится к WASAPI"
            )

        output_name = output["name"]

        devices = list(
            audio.get_loopback_device_info_generator()
        )

        for device in devices:
            name = device["name"].removesuffix(
                " [Loopback]"
            )

            if name.casefold() == output_name.casefold():
                return device

        raise RuntimeError(
            f"Не найден Loopback для устройства: {output_name}"
        )

    def start(self, output_device_index=None):
        with self._lock:
            if self._running:
                raise RuntimeError("Захват уже запущен")

            self._last_error = None
            self.dropped_chunks = 0
            self._stop_event.clear()

            while not self._chunks.empty():
                try:
                    self._chunks.get_nowait()
                except queue.Empty:
                    break

            audio = pyaudio.PyAudio()

            try:
                device = self._find_loopback_device(
                    audio,
                    output_device_index
                )

                self._device_name = device["name"]
                self.sample_rate = int(
                    device["defaultSampleRate"]
                )
                self.channels = int(
                    device["maxInputChannels"]
                )

                if self.channels < 1:
                    raise RuntimeError(
                        "Устройство не поддерживает захват звука"
                    )

                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=device["index"],
                    frames_per_buffer=1024,
                    stream_callback=self._audio_callback,
                    start=False
                )

                self._audio = audio
                self._stream = stream

                stream.start_stream()
                self._running = True

            except Exception:
                try:
                    audio.terminate()
                except Exception:
                    pass

                self._audio = None
                self._stream = None
                self._running = False
                raise

    def _audio_callback(
        self,
        in_data,
        frame_count,
        time_info,
        status_flags
    ):
        if self._stop_event.is_set():
            return (None, pyaudio.paComplete)

        if status_flags:
            self._last_error = (
                f"PortAudio callback status: {status_flags}"
            )

        if in_data:
            chunk = AudioChunk(
                data=in_data,
                captured_at=time.time(),
                sample_rate=self.sample_rate,
                channels=self.channels
            )

            try:
                self._chunks.put_nowait(chunk)

            except queue.Full:
                try:
                    self._chunks.get_nowait()
                    self.dropped_chunks += 1
                except queue.Empty:
                    pass

                try:
                    self._chunks.put_nowait(chunk)
                except queue.Full:
                    self.dropped_chunks += 1

        return (None, pyaudio.paContinue)

    def get_chunk(self, timeout=1.0):
        try:
            return self._chunks.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        with self._lock:
            self._stop_event.set()

            stream = self._stream
            audio = self._audio

            self._stream = None
            self._audio = None
            self._running = False

        if stream is not None:
            try:
                if stream.is_active():
                    stream.stop_stream()
            finally:
                stream.close()

        if audio is not None:
            audio.terminate()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
