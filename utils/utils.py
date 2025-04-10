from datetime import datetime, timedelta
import pandas as pd
import os

def time_to_minutes(t_str):
    h, m = map(int, t_str.split(":"))
    return h * 60 + m

def minutes_to_datetime(m, reference):
    dt = reference + timedelta(minutes=m)
    return dt.strftime("%Y-%m-%d %H:%M")

def is_non_peak(minute_of_day):
    return minute_of_day <= 239 or minute_of_day >= 1200  # 4am–8pm

def print_schedule(schedule):
    """
    Prints the schedule in a structured text format.
    """
    print("\nOptimized Schedule:")
    for entry in schedule:
        print(f"Machine: {entry['machine']} | Patient: {entry['patient_id']} "
              f"({entry['scan_type']}) from {entry['start_time']} to {entry['end_time']} "
              f"(Priority {int(entry['priority'])})")

def append_new_scans_to_schedule(cleaned_schedule, schedule_csv_path):
    if os.path.exists(schedule_csv_path):
        existing_df = pd.read_csv(schedule_csv_path)
        existing_ids = set(existing_df['scan_id'].astype(str))
        new_df = pd.DataFrame(cleaned_schedule)
        new_df = new_df[~new_df['scan_id'].astype(str).isin(existing_ids)]
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        final_df = pd.DataFrame(cleaned_schedule)

    final_df.to_csv(schedule_csv_path, index=False)

def check_for_overlaps(schedule):
    from collections import defaultdict

    machine_sched = defaultdict(list)
    for entry in schedule:
        start = datetime.strptime(entry['start_time'], "%Y-%m-%d %H:%M")
        end = datetime.strptime(entry['end_time'], "%Y-%m-%d %H:%M")
        machine_sched[entry["machine"]].append((start, end, entry['patient_id'], entry['scan_id']))

    for machine, times in machine_sched.items():
        times.sort()
        for i in range(len(times) - 1):
            _, end1, _, id1 = times[i]
            start2, _, _, id2 = times[i + 1]
            if start2 < end1:
                print(f"Problem: Overlap on {machine}: Scan {id1} overlaps with {id2}")

def is_non_peak(minute_of_day):
    """
    Returns True if the given minute (from midnight) falls in non-peak hours (8pm–4am).
    """
    return minute_of_day <= 239 or minute_of_day >= 1200
