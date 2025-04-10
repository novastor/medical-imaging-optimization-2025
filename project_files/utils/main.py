# Developed by Joshua Balisch and Dylan Rouse
# BMG 5109: Medical Systems Innovation and Design

from optimizer import optimize_scan_scheduling
from visualizer import plot_schedule_by_day
from utils import print_schedule, check_for_overlaps
from excel_export import create_machine_agenda_excel

def do_optimization(scan_input):
   # scans_csv_file = 'scans.csv'
    schedule_csv_file = 'current_schedule_multiple_machines.csv'
    print("old input")
    print(scan_input)
    new_schedule = optimize_scan_scheduling(scan_input, schedule_csv_file)
    
    if new_schedule:
        print_schedule(new_schedule)
        plot_schedule_by_day(new_schedule)
        create_machine_agenda_excel(new_schedule)
        check_for_overlaps(new_schedule)
        return new_schedule

    else:
        print("Error: Cannot find a solution.")
