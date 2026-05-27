# -*- coding: utf-8 -*-
import time
from datetime import datetime


def chinese_timestamp():
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )


def nm(value_m):
    return value_m * 1e9


def format_duration(seconds):
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return "{:.1f} s".format(seconds)
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    if minutes < 60:
        return "{} min {} s".format(minutes, sec)
    hours = minutes // 60
    minutes = minutes % 60
    return "{} h {} min {} s".format(hours, minutes, sec)


def describe_point_generic(point):
    parts = []
    if hasattr(point, "direction_name"):
        parts.append("direction={}".format(point.direction_name))
    for attr, label in (
        ("distance_m", "d"),
        ("x_m", "x"),
        ("y_m", "y"),
        ("notch_depth_m", "notch_depth"),
        ("delta_m", "delta"),
        ("rx_m", "Rx"),
        ("ry_m", "Ry"),
        ("radius_x_m", "R_in_x"),
        ("radius_y_m", "R_in_y"),
    ):
        if hasattr(point, attr):
            parts.append("{}={:.3f} nm".format(label, nm(getattr(point, attr))))
    return ", ".join(parts) if parts else str(point)


def print_runtime_progress(done_count, total_count, elapsed_s, run_started_at):
    remaining_count = max(0, total_count - done_count)
    avg_s = (time.time() - run_started_at) / float(max(1, done_count))
    remain_s = avg_s * remaining_count
    print(
        "    单次仿真时间: {}；已完成: {}/{}；还剩 {} 组；预计还需要 {}".format(
            format_duration(elapsed_s),
            done_count,
            total_count,
            remaining_count,
            format_duration(remain_s),
        )
    )
