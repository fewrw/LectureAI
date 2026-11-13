import time

from audio.system_audio_capture import SystemAudioCapture


devices = SystemAudioCapture.list_output_devices()

print("\nДоступные устройства вывода WASAPI:\n")

for device in devices:
    default = " [ПО УМОЛЧАНИЮ]" if device["is_default"] else ""

    print(f"{device['name']}{default}")
    print(f"  Индекс: {device['index']}")

    if device["loopback_available"]:
        print("  Loopback: доступен")
        print(f"  Индекс Loopback: {device['loopback_index']}")
        print(f"  Частота: {device['sample_rate']} Hz")
        print(f"  Каналы: {device['channels']}")
    else:
        print("  Loopback: недоступен")

    print("\nВведите индекс устройства для теста:")

    selected_index = int(input("> "))

    capture = SystemAudioCapture()

    try:
        capture.start(output_device_index=selected_index)

        print("\nЗахват запущен:", capture.device_name)

        start_time = time.monotonic()
        received = 0

        while time.monotonic() - start_time < 5:
            chunk = capture.get_chunk(timeout=0.2)

            if chunk is not None:
                received += 1

        print("Получено сегментов:", received)

    finally:
        capture.stop()
        print("Захват остановлен.")