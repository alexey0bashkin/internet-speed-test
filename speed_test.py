#!/usr/bin/env python3
"""
Простой замер скорости интернета.

Скрипт последовательно выполняет N HTTP-запросов к указанному URL,
замеряет время каждого запроса, считает суммарный объём скачанных
данных и выводит среднюю скорость в МБ/с.
"""

import argparse
import sys
import time
from statistics import mean
from urllib.parse import urlparse

import requests


DEFAULT_URL = "https://images.wallpaperscraft.ru/image/single/gory_skaly_ozero_180314_3840x2400.jpg"  # тяжелый файл по умолчанию
DEFAULT_REQUESTS = 10


def human_bytes(num: float) -> str:
    """Человекочитаемый размер."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024.0:
            return f"{num:3.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} TB"


def measure(url: str, count: int = 10, timeout: int = 60) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        print(f"Ошибка: URL должен начинаться с http:// или https://", file=sys.stderr)
        sys.exit(1)

    print(f"Целевой URL: {url}")
    print(f"Количество запросов: {count}")
    print("-" * 60)

    times: list[float] = []
    total_bytes: int = 0

    # Сессия переиспользует TCP-соединение — так честнее мерить
    # пропускную способность, без оверхеда на handshake каждого раза.
    with requests.Session() as session:
        for i in range(1, count + 1):
            try:
                start = time.perf_counter()
                # stream=False — тянем всё тело сразу, чтобы замерять полное скачивание
                resp = session.get(url, timeout=timeout, stream=False)
                resp.raise_for_status()
                elapsed = time.perf_counter() - start

                size = len(resp.content)
                times.append(elapsed)
                total_bytes += size

                speed_mbps = size / elapsed / (1024 * 1024) if elapsed > 0 else 0.0
                print(
                    f"[{i:>2}/{count}] "
                    f"{elapsed:6.3f} c | "
                    f"{human_bytes(size):>10} | "
                    f"{speed_mbps:7.2f} МБ/с"
                )
            except requests.exceptions.RequestException as e:
                print(f"[{i:>2}/{count}] Ошибка запроса: {e}", file=sys.stderr)

    if not times:
        print("Не удалось выполнить ни одного запроса.", file=sys.stderr)
        sys.exit(1)

    avg_time = mean(times)
    total_time = sum(times)
    avg_speed = (total_bytes / total_time) / (1024 * 1024) if total_time > 0 else 0.0

    print("-" * 60)
    print(f"Успешных запросов:    {len(times)} из {count}")
    print(f"Скачано всего:        {human_bytes(total_bytes)}")
    print(f"Суммарное время:      {total_time:.3f} c")
    print(f"Среднее время запроса:{avg_time:.3f} c")
    print(f"Средняя скорость:     {avg_speed:.2f} МБ/с")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Замер скорости интернета через последовательные HTTP-запросы."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"URL тяжёлого ресурса (по умолчанию: {DEFAULT_URL})",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=DEFAULT_REQUESTS,
        help=f"Количество запросов (по умолчанию: {DEFAULT_REQUESTS})",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=60,
        help="Таймаут одного запроса в секундах (по умолчанию: 60)",
    )
    args = parser.parse_args()

    if args.count <= 0:
        print("Количество запросов должно быть > 0", file=sys.stderr)
        sys.exit(1)

    measure(args.url, args.count, args.timeout)


if __name__ == "__main__":
    main()
