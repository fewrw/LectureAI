
import time

from audio.system_audio_capture import SystemAudioCapture


capture = SystemAudioCapture()

try:
    for cycle in range(1, 4):
        print(f"\n--- Цикл {cycle}/3 ---")

        capture.start()

        print("Захват запущен:", capture.device_name)

        start_time = time.monotonic()
        received = 0

        while time.monotonic() - start_time < 3:
            chunk = capture.get_chunk(timeout=0.2)

            if chunk is not None:
                received += 1

        capture.stop()

        print("Получено сегментов:", received)
        print("Захват остановлен:", not capture.is_running)

        if received == 0:
            raise RuntimeError("Аудиоданные не получены")

        if capture.is_running:
            raise RuntimeError("Захват не остановился")

    print("\nВсе три цикла пройдены.")

except Exception as error:
    print("\nОшибка:", repr(error))

finally:
    capture.stop()
