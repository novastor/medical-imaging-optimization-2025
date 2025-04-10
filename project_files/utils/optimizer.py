import os
import pandas as pd
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from maintenance import bump_priority_zero, insert_maintenance_blocks
from config import machines
from utils import minutes_to_datetime
import io

def optimize_scan_scheduling(scans, schedule_csv_path):
    model = cp_model.CpModel()
    current_time = datetime.now()
    #print((scans))
    print("hello")
    scans_df = pd.read_csv(io.StringIO(scans))
    #print(type(scans_df))
    # --- Step 1: Load New Scan Requests ---
  # scans_df = pd.read_csv(scans)
    scans_df = scans_df.dropna(subset=["check_in_date", "check_in_time"])
    scans_df["check_in_datetime"] = pd.to_datetime(
        scans_df["check_in_date"] + " " + scans_df["check_in_time"],
        format="%Y-%m-%d %H:%M"
    )
    
    # --- Step 2: Determine Reference and Offsets ---
    reference_datetime = scans_df["check_in_datetime"].min()
    scans_df["check_in_mins"] = ((scans_df["check_in_datetime"] - reference_datetime)
                                  .dt.total_seconds() // 60).astype(int)
    scans_df["priority"] = scans_df["priority"].astype(int)
    scans_data_all = scans_df.to_dict('records')
    scans_data_all.sort(key=lambda s: (s["priority"], s["check_in_mins"]))

    # --- Step 3: Load Existing Schedule ---
    existing_schedule = []
    locked_schedule = []
    locked_ids = set()

    if os.path.exists(schedule_csv_path):
        existing_df = pd.read_csv(schedule_csv_path)
        for _, row in existing_df.iterrows():
            if row["scan_type"] == "maintenance":
                continue
            existing_schedule.append(row)
            start_dt = datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M")
            if start_dt < (current_time + timedelta(hours=48)):
                locked_schedule.append(row)
                locked_ids.add(row["scan_id"])

    # --- Step 4: Filter for New Scans ---
    new_scans_data = [s for s in scans_data_all if s["scan_id"] not in locked_ids]

    for s in new_scans_data:
        s["priority"] = int(s["priority"])

    standby_machines = {}
    for scan_type, machine_list in machines.items():
        if len(machine_list) > 1:
            standby_machines[scan_type] = machine_list[-1]

    # --- Step 5: Define Planning Horizon ---
    horizon = (max([s["check_in_mins"] for s in new_scans_data]) if new_scans_data else 0) + 1440

    # --- Step 6: Create Decision Variables ---
    assignment, start_vars, intervals, aux = {}, {}, {}, {}
    for s in new_scans_data:
        s_id = s["scan_id"]
        p_id = s["patient_id"]
        priority = int(s["priority"])
        duration = int(s["duration"])
        check_in = s["check_in_datetime"]
        check_in_mins = s["check_in_mins"]

        assignment[s_id], start_vars[s_id], intervals[s_id] = {}, {}, {}
        if priority == 0:
            aux[s_id] = {}

        deadline_map = {1: 1440, 2: 10080, 3: 43200, 4: 86400, 5: 345600}
        deadline = deadline_map.get(priority, horizon)

        for m in machines[s["scan_type"]]:
            if m in standby_machines.get(s["scan_type"], []) and priority != 1:
                continue

            st = model.NewIntVar(check_in_mins, check_in_mins + deadline, f"start_{s_id}_{m}")
            assignment[s_id][m] = model.NewBoolVar(f"assign_{s_id}_{m}")
            start_vars[s_id][m] = st

            if priority in [4, 5]:
                minute_of_day = model.NewIntVar(0, 1439, f"mod1440_{s_id}_{m}")
                peak_indicator = model.NewBoolVar(f"peak_{s_id}_{m}")

                model.AddModuloEquality(minute_of_day, st, 1440)
                model.AddBoolOr([
                    model.NewBoolVar(f"dummy_true_{s_id}_{m}"),
                    peak_indicator
                ])
                model.Add(minute_of_day >= 240).OnlyEnforceIf(peak_indicator)
                model.Add(minute_of_day <= 1199).OnlyEnforceIf(peak_indicator)
                model.Add(minute_of_day < 240).OnlyEnforceIf(peak_indicator.Not())
                model.Add(minute_of_day > 1199).OnlyEnforceIf(peak_indicator.Not())

                s["peak_indicators"] = s.get("peak_indicators", {})
                s["peak_indicators"][m] = peak_indicator

            intervals[s_id][m] = model.NewOptionalIntervalVar(
                st, duration, st + duration, assignment[s_id][m], f"interval_{s_id}_{m}"
            )

            if priority == 0:
                aux[s_id][m] = model.NewIntVar(0, horizon, f"aux_{s_id}_{m}")
                M = horizon
                model.Add(aux[s_id][m] <= st)
                model.Add(aux[s_id][m] <= M * assignment[s_id][m])
                model.Add(aux[s_id][m] >= st - M * (1 - assignment[s_id][m]))

        if assignment[s_id]:
            model.Add(sum(assignment[s_id][m] for m in assignment[s_id]) == 1)

    # --- Step 7: Ensure One Scan per Patient ---
    patient_to_assignments = {}
    for s in new_scans_data:
        p_id, s_id = s["patient_id"], s["scan_id"]
        patient_to_assignments.setdefault(p_id, [])
        for m in assignment[s_id]:
            patient_to_assignments[p_id].append(assignment[s_id][m])
    for p_id, assigns in patient_to_assignments.items():
        model.Add(sum(assigns) <= 1)

    # --- Step 8: No-Overlap Constraints ---
    locked_intervals_by_machine = {m: [] for m in sum(machines.values(), [])}
    for ls in locked_schedule:
        locked_start_dt = datetime.strptime(ls["start_time"], "%Y-%m-%d %H:%M")
        locked_start = int((locked_start_dt - reference_datetime).total_seconds() // 60)
        dur = int(ls["duration"])
        iv = model.NewIntervalVar(locked_start, dur, locked_start + dur, f"locked_{ls['scan_id']}_{ls['machine']}")
        locked_intervals_by_machine[ls["machine"]].append(iv)

    for cat, m_list in machines.items():
        for m in m_list:
            machine_intervals = []
            for s in new_scans_data:
                s_id = s["scan_id"]
                if m in intervals.get(s_id, {}):
                    machine_intervals.append(intervals[s_id][m])
            machine_intervals += locked_intervals_by_machine.get(m, [])
            if machine_intervals:
                model.AddNoOverlap(machine_intervals)

    # --- Step 9: Objective Function ---
    objective_terms = []
    for s in new_scans_data:
        s_id = s["scan_id"]
        check_in_bias = s["check_in_mins"]
        for m in assignment[s_id]:
            st = start_vars[s_id][m]
            if s["priority"] == 0:
                objective_terms.append(100000 * assignment[s_id][m] - aux[s_id][m])
            else:
                weight = (6 - int(s["priority"])) * 10000
                term = weight * assignment[s_id][m] - st
                if int(s["priority"]) in [4, 5]:
                    peak_indicator = s["peak_indicators"][m]
                    term -= 100000 * peak_indicator
                objective_terms.append(term)
    model.Maximize(sum(objective_terms))

    # --- Step 10: Solve Model ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # --- Step 11: Extract Solution ---
    new_schedule = []
    for s in new_scans_data:
        s_id = s["scan_id"]
        for m in assignment[s_id]:
            if solver.Value(assignment[s_id][m]):
                st = solver.Value(start_vars[s_id][m])
                new_schedule.append({
                    "scan_id": s_id,
                    "patient_id": s["patient_id"],
                    "scan_type": s["scan_type"],
                    "machine": m,
                    "start_time": minutes_to_datetime(st, reference_datetime),
                    "end_time": minutes_to_datetime(st + int(s["duration"]), reference_datetime),
                    "priority": s["priority"],
                    "duration": s["duration"]
                })

    # --- Step 12: Merge new scans with existing ones ---
    existing_ids = set(row["scan_id"] for row in existing_schedule)
    all_scans = existing_schedule + [s for s in new_schedule if s["scan_id"] not in existing_ids]
    all_scans = bump_priority_zero(all_scans)
    all_scans = insert_maintenance_blocks(all_scans)

    # --- Step 13: Clean and Save Final Schedule ---
    cleaned_schedule = []
    for entry in all_scans:
        cleaned_entry = {}
        for key, value in entry.items():
            cleaned_entry[key] = str(value) if isinstance(value, dict) else value
        cleaned_schedule.append(cleaned_entry)

    pd.DataFrame(cleaned_schedule).to_csv(schedule_csv_path, index=False)
    print(type(cleaned_schedule))
    print(cleaned_schedule)
    return cleaned_schedule
