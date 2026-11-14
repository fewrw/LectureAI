
import time

from screen.teams_window_monitor import TeamsWindowMonitor


def main():
    monitor = TeamsWindowMonitor()

    print("Мониторинг Teams запущен.")
    print("Продолжительность: 40 секунд.\n")

    previous_state = None

    for second in range(40):
        state = monitor.find_window()

        if state is None:
            current_state = "not_found"
            description = "ОКНО TEAMS НЕ НАЙДЕНО"

        elif state.is_minimized:
            current_state = "minimized"
            description = "TEAMS СВЁРНУТ"

        else:
            current_state = "normal"
            description = "TEAMS РАЗВЁРНУТ"

        if current_state != previous_state:
            print(
                f"[{second:02d} сек.] {description}"
            )

            previous_state = current_state

        time.sleep(1)

    print("\nТест завершён.")


if __name__ == "__main__":
    main()
