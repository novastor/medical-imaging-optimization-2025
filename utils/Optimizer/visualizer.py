import matplotlib.pyplot as plt
from datetime import datetime, timedelta


def plot_schedule_by_day(schedule):
    """
    Groups the schedule by day (based on the date in 'start_time')
    and generates a separate visual agenda for each day, saving each as "visual_schedule_<day>.png".
    """
    schedule_by_day = {}
    for entry in schedule:
        day = entry["start_time"].split()[0]
        schedule_by_day.setdefault(day, []).append(entry)

    for day, day_schedule in schedule_by_day.items():
        plot_day_schedule(day_schedule, day)


def plot_day_schedule(day_schedule, day):
    """
    Plots the schedule for a single day in an agenda view.
    """
    if not day_schedule:
        return

    # --- Determine the time axis bounds ---
    booked_times = []
    for entry in day_schedule:
        st = datetime.strptime(entry["start_time"], "%Y-%m-%d %H:%M")
        et = datetime.strptime(entry["end_time"], "%Y-%m-%d %H:%M")
        booked_times.extend([st, et])
    min_booking = min(booked_times)
    max_booking = max(booked_times)

    min_booking = min_booking.replace(minute=(min_booking.minute // 5) * 5, second=0, microsecond=0)
    total_max = max_booking.hour * 60 + max_booking.minute
    rounded_max = ((total_max + 4) // 5) * 5
    max_booking = max_booking.replace(hour=rounded_max // 60, minute=rounded_max % 60, second=0, microsecond=0)

    total_intervals = ((max_booking - min_booking).seconds // (5 * 60)) + 1
    time_intervals = [min_booking + timedelta(minutes=5 * i) for i in range(total_intervals)]
    time_labels = [t.strftime("%H:%M") for t in time_intervals]

    # --- Machine axis ---
    machines_order = sorted(set(entry["machine"] for entry in day_schedule))

    fig, ax = plt.subplots(figsize=(12, 16))
    ax.set_yticks(range(len(time_intervals)))
    ax.set_yticklabels(time_labels, fontsize=9)
    ax.set_xticks(range(len(machines_order)))
    ax.set_xticklabels(machines_order, fontsize=12)
    ax.set_ylim(-1, len(time_intervals))

    for y in range(len(time_intervals)):
        ax.axhline(y, color="gray", linestyle="--", linewidth=0.5, alpha=0.7)

    # --- Priority color mapping ---
    priority_colors = {
        0: "purple",  # Priority 0
        1: "red",  # Priority 1
        2: "orange",  # Priority 2
        3: "yellow",  # Priority 3
        4: "green",  # Priority 4
        5: "blue"  # Priority 5
    }

    for entry in day_schedule:
        machine = entry["machine"]
        machine_index = machines_order.index(machine)
        st = datetime.strptime(entry["start_time"], "%Y-%m-%d %H:%M")
        et = datetime.strptime(entry["end_time"], "%Y-%m-%d %H:%M")
        start_idx = int((st - min_booking).total_seconds() // (5 * 60))
        duration_blocks = int((et - st).total_seconds() // (5 * 60))

        if entry["scan_type"] == "maintenance":
            color = "black"
        else:
            color = priority_colors.get(int(entry["priority"]), "gray")

        ax.barh(start_idx, width=0.8, height=duration_blocks, left=machine_index - 0.4,
                color=color, edgecolor="black", alpha=0.75)

        label_text = f"{entry['patient_id']}\n{entry['scan_type']}\nP{int(entry['priority'])}"
        text_color = "white" if color in ["black", "purple"] else "black"

        ax.text(machine_index, start_idx + duration_blocks / 2,
                label_text, ha="center", va="center", fontsize=9,
                color=text_color, weight="bold")

    ax.invert_yaxis()
    ax.set_ylabel("Time")
    ax.set_xlabel("Machines")
    ax.set_title(f"Scheduled Scans for {day}")
    fig.tight_layout()
    fig.savefig(f"visual_schedule_{day}.png")
    plt.close(fig)
