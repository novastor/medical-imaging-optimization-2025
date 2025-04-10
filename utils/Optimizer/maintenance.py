from datetime import datetime, timedelta

def bump_priority_zero(schedule):
    """
    For each machine, if a Priority 0 scan is scheduled, bump any subsequent appointment
    that starts before its end. This ensures Priority 0 scans can take effect immediately
    if possible, without interrupting an ongoing scan.
    """
    # Group by machine
    machine_sched = {}
    for appt in schedule:
        m = appt["machine"]
        machine_sched.setdefault(m, []).append(appt)

    for m, appts in machine_sched.items():
        # Sort chronologically
        appts.sort(key=lambda a: datetime.strptime(a["start_time"], "%Y-%m-%d %H:%M"))
        i = 0
        while i < len(appts):
            appt = appts[i]
            if int(appt["priority"]) == 0:
                p0_end = datetime.strptime(appt["end_time"], "%Y-%m-%d %H:%M")
                j = i + 1
                while j < len(appts):
                    next_appt = appts[j]
                    next_start = datetime.strptime(next_appt["start_time"], "%Y-%m-%d %H:%M")
                    next_duration = timedelta(minutes=int(next_appt["duration"]))
                    if next_start < p0_end:
                        # Bump the next appointment to start after Priority 0 ends
                        new_start = p0_end
                        new_end = new_start + next_duration
                        next_appt["start_time"] = new_start.strftime("%Y-%m-%d %H:%M")
                        next_appt["end_time"] = new_end.strftime("%Y-%m-%d %H:%M")
                        p0_end = new_end
                        j += 1
                    else:
                        break
                i = j
            else:
                i += 1
        machine_sched[m] = appts

    # Recombine
    merged = []
    for m in machine_sched:
        merged.extend(machine_sched[m])
    merged.sort(key=lambda x: (x["machine"], datetime.strptime(x["start_time"], "%Y-%m-%d %H:%M")))
    return merged


def insert_maintenance_blocks(schedule):
    """
    Inserts a 60-minute maintenance block after every 20 non-maintenance scans per machine.
    Returns a new schedule with maintenance entries added.
    """
    machine_schedules = {}
    for entry in schedule:
        m = entry["machine"]
        machine_schedules.setdefault(m, []).append(entry)

    for m in machine_schedules:
        machine_schedules[m].sort(key=lambda x: datetime.strptime(x["start_time"], "%Y-%m-%d %H:%M"))

    final_schedule = []
    for m, entries in machine_schedules.items():
        count = 0
        for entry in entries:
            if entry["scan_type"] != "maintenance":
                count += 1
            final_schedule.append(entry)
            if count > 0 and count % 20 == 0:
                maint_start = datetime.strptime(entry["end_time"], "%Y-%m-%d %H:%M")
                maint_end = maint_start + timedelta(minutes=60)
                maint_entry = {
                    "scan_id": f"maintenance_{m}_{count}",
                    "patient_id": "Maintenance",
                    "scan_type": "maintenance",
                    "machine": m,
                    "start_time": maint_start.strftime("%Y-%m-%d %H:%M"),
                    "end_time": maint_end.strftime("%Y-%m-%d %H:%M"),
                    "priority": 0,
                    "duration": 60
                }
                final_schedule.append(maint_entry)

    final_schedule.sort(key=lambda x: (x["machine"], datetime.strptime(x["start_time"], "%Y-%m-%d %H:%M")))
    return final_schedule
