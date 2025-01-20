import os
import pm4py
import pandas as pd
from datetime import datetime

from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.conformance import fitness_alignments
import importlib.util
from tqdm import tqdm
import json

from config import *
from utils import prepare_df, get_days_of_year_week

def build_petri_net_for_week(prev, year_week_department):
  year, week = int(year_week_department.split('-')[0]), int(year_week_department.split('-')[1])
  dates = get_days_of_year_week(year, week)

  # get operations only of specific department, year and week
  ops = prev[prev[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department]
  ops = prepare_df(ops, activity_key=ACTIVITY_KEY, timestamp_key=TIMESTAMP_KEY)

  # setup pretri net
  net = PetriNet(year_week_department)

  # previous day transition
  prev_day_t = None

  # previous day places
  prev_day_ps = []

  # source place
  source = PetriNet.Place(f'{dates[0]}')
  net.places.add(source)

  # for each date
  for day_idx, date in enumerate(dates):
    ops_date = ops[ops[TIMESTAMP_KEY] == date]

    next_day_t = PetriNet.Transition(date, f'{date}')
    net.transitions.add(next_day_t)

    if day_idx == 0:
      petri_utils.add_arc_from_to(source, next_day_t, net)
    else:
      # arcs from prev day places to current day transition
      if len(prev_day_ps) > 0:
        for prev_day_p in prev_day_ps:
          petri_utils.add_arc_from_to(prev_day_p, next_day_t, net)
        
        prev_day_ps = []
      else:
        p = PetriNet.Place(f'{date}-empty')
        net.places.add(p)
        petri_utils.add_arc_from_to(prev_day_t, p, net)
        petri_utils.add_arc_from_to(p, next_day_t, net)

    # for each operation on that date
    for _, op_date in ops_date.iterrows():
      p1 = PetriNet.Place(f'{date}-{op_date[ACTIVITY_KEY]}-1')
      p2 = PetriNet.Place(f'{date}-{op_date[ACTIVITY_KEY]}-2')

      prev_day_ps.append(p2)

      t = PetriNet.Transition(op_date[ACTIVITY_KEY], f'{op_date[ACTIVITY_KEY]}')

      net.places.add(p1)
      net.places.add(p2)
      net.transitions.add(t)

      petri_utils.add_arc_from_to(next_day_t, p1, net)
      petri_utils.add_arc_from_to(p1, t, net)
      petri_utils.add_arc_from_to(t, p2, net)

    prev_day_t = next_day_t

  # add sink
  sink = PetriNet.Place('sink')
  net.places.add(sink)
  petri_utils.add_arc_from_to(prev_day_t, sink, net)

  # insert token in source
  im = Marking()
  im[source] = 1

  fm = Marking()
  fm[sink] = 1

  return net, im, fm

def get_real_fitness(f, f_dummy):
  return (f - f_dummy) / (1 - f_dummy)

def compute_alignment(
  dataset,
  output_path='output',
  output_filename='results.json',
  urgency_types_to_consider=['Elezione'],
  should_consider_reserves=True,
  should_save_petri_nets=False
):
  print('Computing alignments...')
  
  # keep only specified types of operations
  dataset = dataset[dataset[URGENCY_TYPE_KEY].isin(urgency_types_to_consider)]

  year_week_department_list = dataset[YEAR_WEEK_DEPARTMENT_KEY].unique().tolist()
  results = {}
  skipped = []

  for year_week_department in tqdm(year_week_department_list):
    # separa operazioni preventivate da effettuate
    prev, act = dataset[dataset[SLICE_KEY] == SLICE_PREV_VAL], dataset[dataset[SLICE_KEY] == SLICE_ACTUAL_VAL]

    if prev[prev[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department].empty or act[act[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department].empty:
      skipped.append(year_week_department)
      continue

    # costruisci la petri net
    net, im, fm = build_petri_net_for_week(
      prev,
      year_week_department
    )

    if should_save_petri_nets:
      petri_nets_path = os.path.join(output_path, 'petri_nets', '_'.join(urgency_types_to_consider))
      if importlib.util.find_spec('graphviz'):
        if not os.path.exists(petri_nets_path):
          os.makedirs(petri_nets_path)
        
        pm4py.save_vis_petri_net(net, im, fm, os.path.join(petri_nets_path, f'{year_week_department}-{should_consider_reserves}.svg'))

      # generate traces from petrinet
      # log = pm4py.play_out(net, im, fm)
      # pm4py.write_xes(log, f'{year_week_department}.xes')

    # filtra per year_week_department
    act = act[act[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department]
    act = prepare_df(act, activity_key=ACTIVITY_KEY, timestamp_key=TIMESTAMP_KEY)

    # add 'days' activities
    new_act = []

    year, week = int(year_week_department.split('-')[0]), int(year_week_department.split('-')[1])
    dates = get_days_of_year_week(year, week)

    # dummy log with only 'days' activities
    dummy_log = []
    for date in dates:
      new_row = { col: None for col in act.columns }
      new_row[ACTIVITY_KEY] = date
      new_row[TIMESTAMP_KEY] = datetime.strptime(date, '%Y-%m-%d')
      new_row[YEAR_WEEK_DEPARTMENT_KEY] = year_week_department
      dummy_log.append(new_row)

    dummy_log = pd.DataFrame(dummy_log)
    dummy_log[ACTIVITY_KEY] = dummy_log[ACTIVITY_KEY].astype(str)
    dummy_log[TIMESTAMP_KEY] = pd.to_datetime(dummy_log[TIMESTAMP_KEY], format='%Y-%m-%d')

    act_first_date = act[TIMESTAMP_KEY].iloc[0].to_pydatetime()
    act_last_date = act[TIMESTAMP_KEY].iloc[-1].to_pydatetime()

    # add events for change of day
    for date in dates:
      if datetime.strptime(date, '%Y-%m-%d') <= act_first_date:
        new_row = { col: None for col in act.columns }
        new_row[ACTIVITY_KEY] = date
        new_row[TIMESTAMP_KEY] = datetime.strptime(date, '%Y-%m-%d')
        new_row[YEAR_WEEK_DEPARTMENT_KEY] = year_week_department
        new_act.append(new_row)
      else:
        break


    for i in range(len(act) - 1):
      new_act.append(act.iloc[i])

      if act[TIMESTAMP_KEY].iloc[i] != act[TIMESTAMP_KEY].iloc[i+1]:
        new_row = { col: None for col in act.columns }

        current_date = act[TIMESTAMP_KEY].iloc[i]
        next_date = act[TIMESTAMP_KEY].iloc[i+1]
        for date in dates:
          if datetime.strptime(date, '%Y-%m-%d') > current_date and datetime.strptime(date, '%Y-%m-%d') <= next_date:
            new_row = { col: None for col in act.columns }
            new_row[ACTIVITY_KEY] = date
            new_row[TIMESTAMP_KEY] = datetime.strptime(date, '%Y-%m-%d')
            new_row[YEAR_WEEK_DEPARTMENT_KEY] = year_week_department
            new_act.append(new_row)
          else:
            continue
    
    new_act.append(act.iloc[-1])

    for date in dates:
      if datetime.strptime(date, '%Y-%m-%d') <= act_last_date:
        continue
      else:
        new_row = { col: None for col in act.columns }
        new_row[ACTIVITY_KEY] = date
        new_row[TIMESTAMP_KEY] = datetime.strptime(date, '%Y-%m-%d')
        new_row[YEAR_WEEK_DEPARTMENT_KEY] = year_week_department
        new_act.append(new_row)

    new_act = pd.DataFrame(new_act)
    new_act[ACTIVITY_KEY] = new_act[ACTIVITY_KEY].astype(str)
    new_act[TIMESTAMP_KEY] = pd.to_datetime(new_act[TIMESTAMP_KEY], format='%Y-%m-%d')

    # conformance checking
    act_alignment_res = fitness_alignments(
      new_act,
      net,
      im,
      fm,
      multi_processing=False,
      activity_key=ACTIVITY_KEY,
      case_id_key=YEAR_WEEK_DEPARTMENT_KEY,
      timestamp_key=TIMESTAMP_KEY,
    )

    dummy_alignment_res = fitness_alignments(
      dummy_log,
      net,
      im,
      fm,
      multi_processing=False,
      activity_key=ACTIVITY_KEY,
      case_id_key=YEAR_WEEK_DEPARTMENT_KEY,
      timestamp_key=TIMESTAMP_KEY,
    )

    # perform some trick to get real fitness
    alignment_res = {}
    for key in act_alignment_res.keys():
      alignment_res[key] = get_real_fitness(act_alignment_res[key], dummy_alignment_res[key])

    results[year_week_department] = alignment_res

  # save results to json file
  with open(os.path.join(output_path, output_filename), 'w') as f:
    json.dump(results, f, indent=2)
