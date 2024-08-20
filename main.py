import pandas as pd
import pm4py
import datetime
import matplotlib.pyplot as plt


SLICE_KEY = 'SLICE'
SLICE_PREV_VAL = 'preventivato'
SLICE_ACTUAL_VAL = 'actual'

EMERGENCY_KEY = 'TIPO_URGENZA'
EMERGENCY_URGENCY_VAL = 'Urgenza'
EMERGENCY_EMERGENCY_VAL = 'Emergenza'
EMERGENCY_ELECTION_VAL = 'Elezione'

dataset = pd.read_csv('dataset.csv', sep=';', encoding='iso-8859-1')

# filtra tra preventivate e actual
prev, actual = dataset[dataset[SLICE_KEY] == SLICE_PREV_VAL], dataset[dataset[SLICE_KEY] == SLICE_ACTUAL_VAL]

assert len(prev) + len(actual) == len(dataset)

# quante operazioni actual erano state preventivate?
actual_prev, actual_not_prev = actual[actual['LKP_PAZ_DATA_PREV-ACT'] == 1], actual[actual['LKP_PAZ_DATA_PREV-ACT'] == 0]
num_actual_prev, num_actual_not_prev = len(actual_prev), len(actual_not_prev)

assert num_actual_prev + num_actual_not_prev == len(actual)

print(f'Operazioni effetuate: {len(actual)}, di cui preventivate: {(num_actual_prev / len(actual) * 100):.1f}%')

# tra le operazioni non preventivate, quante sono urgenze e quante emergenze?
num_urgencies_not_prev = len(actual_not_prev[actual_not_prev[EMERGENCY_KEY] == EMERGENCY_URGENCY_VAL])
num_emergencies_not_prev = len(actual_not_prev[actual_not_prev[EMERGENCY_KEY] == EMERGENCY_EMERGENCY_VAL])
num_election_not_prev = len(actual_not_prev[actual_not_prev[EMERGENCY_KEY] == EMERGENCY_ELECTION_VAL])

print(f'Operazioni effettuate ma non preventivate: {len(actual_not_prev)}')
print(f'Di cui emergenze: {num_emergencies_not_prev}, urgenze: {num_urgencies_not_prev}, elezione: {num_election_not_prev}')

# non ci dovrebbero essere, tra le operazioni preventivate, delle emergenze
num_emergencies_prev = len(actual_prev[actual_prev[EMERGENCY_KEY] == EMERGENCY_EMERGENCY_VAL])

print(f'Tra le operazioni preventivate ci sono state {num_emergencies_prev} emergenze.')

# costruiamo un log usando come case id la combinazione di data+sala

# def is_valid_datetime_format(date_string):
#   try:
#     datetime.datetime.strptime(date_string, '%d/%m/%Y %H:%M')
#     return True
#   except ValueError:
#     return False

# def conform_datetime(row):
#   if not is_valid_datetime_format(row['ENTRATA_SALA']):
#     # Number of days since January 1, 1900
#     days_since_1900, seconds_since_midnight = row['ENTRATA_SALA'].split(',')
#     days_since_1900 = int(days_since_1900)
#     seconds_since_midnight = int(seconds_since_midnight)

#     # Start date
#     start_date = datetime.datetime(1900, 1, 1)

#     # Calculate the new date
#     new_date = start_date + datetime.timedelta(days=days_since_1900, seconds=seconds_since_midnight)

#     # Format datetime
#     formatted_date = new_date.strftime('%d/%m/%Y %H:%M')

#     # Apply the new value to the dataframe
#     row['ENTRATA_SALA'] = formatted_date

#   return row

# actual = actual.apply(lambda row: conform_datetime(row), axis=1)

# actual['ENTRATA_SALA'] = pd.to_datetime(actual['ENTRATA_SALA'], format="%d/%m/%Y %H:%M")

# pm4py.write_xes(actual, 'log.xes', case_id_key='Data_Sala')



# per ogni giornata, calcolare quanto tempo viene utilizzata ogni sala
# poi, calcolare la media di utilizzo di ogni sala e confrontarla con il tempo
days_and_rooms = actual['Data_Sala'].unique()

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
  facts = actual[actual['Data_Sala'] == day_and_room]

  # count number of operations performed
  room_usage_per_day[date][room]['num_operations'] = len(facts)

  # count number of hours that the room has been used in that day
  facts['T_OCCUP_SALA'] = facts['T_OCCUP_SALA'].str.replace(',', '.').astype(float)
  room_usage_per_day[date][room]['usage'] = facts['T_OCCUP_SALA'].sum() * 24


# Initialize a dictionary to store total usage and count of days for each room
room_usage_total = {}

# Iterate over each date in the room_usage dictionary
for date, rooms in room_usage_per_day.items():
    for room, data in rooms.items():
        room = int(room)
        if room not in room_usage_total:
            room_usage_total[room] = {'total_usage': 0, 'count': 0, 'usages': []}
        room_usage_total[room]['total_usage'] += data['usage']
        room_usage_total[room]['count'] += 1
        room_usage_total[room]['usages'].append(data['usage'])

# Prepare data for boxplot
room_usages = [room_usage_total[room]['usages'] for room in sorted(room_usage_total.keys())]

# Create boxplot
plt.figure(figsize=(10, 6))
plt.boxplot(room_usages, patch_artist=True)

# Add labels and title
plt.xlabel('Room Index')
plt.ylabel('Usage (hours)')
plt.title('Room Usage Distribution')
plt.xticks(ticks=range(1, len(room_usages) + 1), labels=sorted(room_usage_total.keys()), rotation=45)
plt.tight_layout()
plt.show()

print('a')