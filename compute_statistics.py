import pandas as pd
import datetime
import matplotlib.pyplot as plt

from config import *

def plot_boxplot(data, labels, ylabel, title):
  # Create boxplot
  plt.figure(figsize=(10, 6))
  plt.boxplot(data, patch_artist=True)

  # Add labels and title
  plt.xlabel('Codice sala')
  plt.ylabel(ylabel)
  plt.title(title)
  plt.xticks(ticks=range(1, len(data) + 1), labels=labels, rotation=0)
  plt.tight_layout()
  plt.show()


# what_to_plot can be either 'usage' or 'num_operations'
def compute_room_usage(data, what_to_plot='usage'):
  days_and_rooms = data['Data_Sala'].unique()
  room_usage_per_day = {}

  for day_and_room in days_and_rooms:
    day, room = day_and_room.split('-')

    # convert day number to date
    start_date = datetime.datetime(1900, 1, 1)
    date = start_date + datetime.timedelta(days=int(day))
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
    ylabel = 'Utilizzo sala (ore)'
    title = 'Utilizzo medio (ore) per sala'
  elif what_to_plot == 'num_operations':
    ylabel = 'Numero operazioni'
    title = 'Numero operazioni medio per sala'
  
  plot_boxplot(
    [usage_per_room[room][what_to_plot] for room in sorted(usage_per_room.keys())],
    labels=sorted(usage_per_room.keys()),
    ylabel=ylabel,
    title=title
  )


# load dataset
dataset = pd.read_csv('dataset.csv', sep=';', encoding='iso-8859-1')

# keep only actual operations
actual = dataset[dataset[SLICE_KEY] == SLICE_ACTUAL_VAL]

# compute statistics
compute_room_usage(actual, what_to_plot='num_operations')