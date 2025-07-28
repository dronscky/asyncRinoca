


def get_delay_time(attempt: int) -> int:
    match attempt:
        case 0:
            delay = 30
        case 1:
            delay = 60
        case 2:
            delay = 90
        case _:
            delay = 180
    return delay
