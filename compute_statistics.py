import pandas as pd
from datetime import datetime, timedelta, time
import matplotlib.pyplot as plt

from config import *

def plot_boxplot(data, labels, xlabel, ylabel, title, xticks_rotation=0):
  # Create boxplot
  plt.figure(figsize=(10, 6))
  plt.boxplot(data, patch_artist=True)

  # Add labels and title
  plt.xlabel(xlabel)
  plt.ylabel(ylabel)
  plt.title(title)
  plt.xticks(ticks=range(1, len(data) + 1), labels=labels, rotation=xticks_rotation)
  plt.tight_layout()
  plt.show()


def plot_barplot(data, labels, xlabel, ylabel, title, xticks_rotation=0):
  # Create bar plot
  plt.figure(figsize=(10, 6))
  plt.bar(range(len(data)), data, tick_label=labels)

  # Add labels and title
  plt.xlabel(xlabel)
  plt.ylabel(ylabel)
  plt.title(title)
  plt.xticks(rotation=xticks_rotation)
  plt.tight_layout()
  plt.show()


# what_to_plot can be either 'usage' or 'num_operations'
def compute_room_usage(data, what_to_plot='usage'):
  days_and_rooms = data['Data_Sala'].unique()
  room_usage_per_day = {}

  for day_and_room in days_and_rooms:
    day, room = day_and_room.split('-')

    # convert day number to date
    start_date = datetime(1900, 1, 1)
    date = start_date + timedelta(days=int(day))
    date = date.strftime('%d/%m/%Y')

    # create dict to store info about that date
    if date not in room_usage_per_day:
      room_usage_per_day[date] = {}

    room_usage_per_day[date][room] = {}

    # get operations performed on that date and room
    facts = data[data['Data_Sala'] == day_and_room]

    # count number of operations performed
    room_usage_per_day[date][room]['num_operations'] = len(facts)

    # count number of hours that the room has been used in that day
    facts['T_OCCUP_SALA'] = facts['T_OCCUP_SALA'].str.replace(',', '.').astype(float)
    room_usage_per_day[date][room]['usage'] = facts['T_OCCUP_SALA'].sum() * 24


  usage_per_room = {}

  for date, rooms in room_usage_per_day.items():
    for room, data in rooms.items():
      room = int(room)
      if room not in usage_per_room:
        usage_per_room[room] = { 'usage': [], 'num_operations': [] }

      usage_per_room[room]['usage'].append(data['usage'])
      usage_per_room[room]['num_operations'].append(data['num_operations'])


  if what_to_plot == 'usage':
    ylabel = 'Room usage (hours)'
    title = 'Usage by room (day average)'
  elif what_to_plot == 'num_operations':
    ylabel = 'Operation number'
    title = 'Operation number by room (day average)'
  
  plot_boxplot(
    [usage_per_room[room][what_to_plot] for room in sorted(usage_per_room.keys())],
    labels=sorted(usage_per_room.keys()),
    xlabel='Room code',
    ylabel=ylabel,
    title=title
  )


# leggo il file DIM_TURNI_REPARTO.csv
# per ogni DATA
  # vado su dataset.csv, scartando preventivati e tenendo solo actual, filtro per DATA
  # (opzionale: rimuovo urgenze ed emergenze, oppure: rimuovo operazioni con LKP_PAZ_DATA_PREV-ACT=0 perché non erano state preventivate)
  # leggo i reparti e la rispettiva sala. in dataset, filtro tenendo solo le operazioni di quei reparti (attenzione: può capitare che in actual siano usate due sale operatorie diverse per stesso reparto. come gestisco tale caso? non considero in actual le operazioni di quel reparto in sale diverse da quelle preventivate in DIM_TURNI_REPARTO?)
  # calcolo il numero di minuti actual al di fuori del range preventivato in DIM_TURNI_REPARTO. tale numero è l'overtime di quel giorno per quel reparto
# mi troverò con un dict del tipo seguente
# results = {
#   '01/01/2020': {
#     'Ortopedia': 120,
#     'Chirurgia 1': 60,
#     ...
#   },
#   '02/01/2020': {
#     ...
#   },
#   ...
# }
# a questo punto posso fare più plot: (1) ritardo medio giornaliero per ciascun reparto, magari con un boxplot, oppure (2) ritardo per ciascuna settimana scomposto nei reparti che hanno causato tale ritardo (istogramma, con ogni barra che rappresenta una settimana e ha più colori uno per reparto)
def compute_usage_and_overtime(actual, schedule_dataset_path='DIM_TURNI_REPARTO.csv'):
  results = {}
  
  schedule = pd.read_csv(schedule_dataset_path, sep=';', encoding='iso-8859-1')

  dates = schedule[TIMESTAMP_KEY].unique().tolist()

  for date in dates:
    if type(date) is not str:
      continue

    results[date] = {}
    day, month, year = [int(part) for part in date.split('/')]

    schedules_on_date = schedule[schedule[TIMESTAMP_KEY] == date]
    operations_on_date = actual[actual[TIMESTAMP_KEY] == date]

    # remove operations that weren't scheduled (i.e. urgencies, emergencies, and some elections)
    operations_on_date = operations_on_date[operations_on_date['LKP_PAZ_DATA_PREV-ACT'] == 1]

    for _, department_schedule in schedules_on_date.iterrows():
      department, room = department_schedule['REPARTO'], department_schedule['SALA_PREV_EX_POST']
      
      # NOTA: qui stiamo escludendo le operazioni actual di department che però sono state eseguite in un'altra sala (può succedere, ma come mai?)
      operations_on_date_on_department_and_room = operations_on_date[(operations_on_date['REPARTO'] == department) & (operations_on_date['COD_SALA'] == room)]

      scheduled_time = (
        datetime(year, month, day, int(department_schedule['TURNO_START']), 0),
        datetime(year, month, day, int(department_schedule['TURNO_END']), 0)
      )
      
      actual_times = []

      for _, operation in operations_on_date_on_department_and_room.iterrows():
        date_format = '%d/%m/%Y %H:%M'

        # NOTA: ho scelto di usare ENTRATA_SALA invece di ENTRATA_GRUPPO ad esempio
        actual_times.append((
          datetime.strptime(operation['ENTRATA_SALA'], date_format),
          datetime.strptime(operation['USCITA_SALA'], date_format)
        ))

      # Helper function to calculate overlap between two intervals
      def overlap(interval1, interval2):
        start1, end1 = interval1
        start2, end2 = interval2
        
        start = max(start1, start2)
        end = min(end1, end2)
        
        # If the intervals overlap, return the overlap duration, otherwise return 0
        return max(timedelta(0), end - start)

      # Helper function to calculate the duration of an interval
      def interval_duration(interval):
        start, end = interval

        return end - start
      

      # Function to calculate usage and overtime
      def calculate_usage_overtime(scheduled_interval, actual_interval):
        # Calculate overlap
        usage = overlap(scheduled_interval, actual_interval)
        
        # Calculate overtime
        overtime = timedelta(0)
        start_scheduled_interval, end_scheduled_interval = scheduled_interval
        start_actual_interval, end_actual_interval = actual_interval
        
        if start_actual_interval < start_scheduled_interval:
            overtime += (start_scheduled_interval - start_actual_interval)
        if end_actual_interval > end_scheduled_interval:
            overtime += (end_actual_interval - end_scheduled_interval)
        
        return usage, overtime
      

      # Check whether there are any overlaps in actual_times
      # If there is at least 1, then skip the computations (it's a dataset problem: there shouldn't be 2 operations performed on the same time in the same room!)
      should_skip_computation = False

      for i in range(len(actual_times)):
        for j in range(i+1, len(actual_times)):
          usage, _ = calculate_usage_overtime(actual_times[i], actual_times[j])

          if usage.total_seconds() > 0:
            print(f'Skipping {department} on {date} because of overlapping operations on times {actual_times[i]} and {actual_times[j]}')
            print(operations_on_date_on_department_and_room)
            should_skip_computation = True

      if should_skip_computation: continue
      
      # Compute usage and overtime
      department_usage, department_overtime = timedelta(0), timedelta(0)

      for actual_time in actual_times:
        operation_usage, operation_overtime = calculate_usage_overtime(scheduled_time, actual_time)
        department_usage += operation_usage
        department_overtime += operation_overtime

      department_usage_perc = department_usage.total_seconds() / interval_duration(scheduled_time).total_seconds()

      if len(actual_times) == 0: continue
      if department_usage_perc > 1.0:
        print(f'Skipping {department} on {date} because usage > 1 ({department_usage_perc})')
        continue

      # populate the results dict
      results[date][department] = {
        'usage': department_usage_perc,
        'overtime': department_overtime.total_seconds(),
      }

  return results


def plot_usage_and_overtime_by_department(results):
  usage_and_overtime_by_department = {}

  for result_on_date in results.values():
    for department, department_on_date in result_on_date.items():
      if department not in usage_and_overtime_by_department:
        usage_and_overtime_by_department[department] = {
          'usages': [],
          'overtimes': [],
        }

      usage_and_overtime_by_department[department]['usages'].append(department_on_date['usage'])
      usage_and_overtime_by_department[department]['overtimes'].append(department_on_date['overtime'] / 60) # convert seconds to minutes

  for department, department_result in usage_and_overtime_by_department.items():
    usage_and_overtime_by_department[department]['usage'] = sum(department_result['usages']) / len(department_result['usages'])
    usage_and_overtime_by_department[department]['overtime'] = sum(department_result['overtimes']) / len(department_result['overtimes'])

  # sort usage_and_overtime_by_department dict by key (alphabetical order)
  usage_and_overtime_by_department = dict(sorted(usage_and_overtime_by_department.items()))

  plot_boxplot(
    [dep['usages'] for dep in usage_and_overtime_by_department.values()],
    labels=list(usage_and_overtime_by_department.keys()),
    xlabel='Department',
    ylabel='Usage (%)',
    title='Usage by department (day average)',
    xticks_rotation=90,
  )

  plot_barplot(
    [dep['overtime'] for dep in usage_and_overtime_by_department.values()],
    labels=list(usage_and_overtime_by_department.keys()),
    xlabel='Department',
    ylabel='Overtime (minutes)',
    title='Overtime by department (day average)',
    xticks_rotation=90,
  )



# load dataset
dataset = pd.read_csv('dataset.csv', sep=';', encoding='iso-8859-1')

# keep only actual operations
actual, prev = dataset[dataset[SLICE_KEY] == SLICE_ACTUAL_VAL], dataset[dataset[SLICE_KEY] == SLICE_PREV_VAL]

# compute statistics
compute_room_usage(actual, what_to_plot='usage')
compute_room_usage(actual, what_to_plot='num_operations')

results = compute_usage_and_overtime(actual, schedule_dataset_path='./DIM_TURNI_REPARTO.csv')

plot_usage_and_overtime_by_department(results)