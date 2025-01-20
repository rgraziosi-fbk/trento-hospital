import os
import pm4py
import pandas as pd
from datetime import datetime

from pm4py.conformance import fitness_alignments
import importlib.util
from tqdm import tqdm
import json

from config import *
from build_petri_net import build_petri_net_for_week
from utils import prepare_df, get_days_of_year_week


def create_dummy_log(year, week, year_week_department, columns):
  dummy_log = []
  dates = get_days_of_year_week(year, week)

  for date in dates:
    new_row = { col: None for col in columns }
    new_row[ACTIVITY_KEY] = date
    new_row[TIMESTAMP_KEY] = datetime.strptime(date, '%Y-%m-%d')
    new_row[YEAR_WEEK_DEPARTMENT_KEY] = year_week_department
    dummy_log.append(new_row)

  dummy_log = pd.DataFrame(dummy_log)
  dummy_log[ACTIVITY_KEY] = dummy_log[ACTIVITY_KEY].astype(str)
  dummy_log[TIMESTAMP_KEY] = pd.to_datetime(dummy_log[TIMESTAMP_KEY], format='%Y-%m-%d')

  return dummy_log


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
      year_week_department,
      year_week_department_key=YEAR_WEEK_DEPARTMENT_KEY,
      activity_key=ACTIVITY_KEY,
      timestamp_key=TIMESTAMP_KEY,
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
      if datetime.strptime(date, '%Y-%m-%d') > act_last_date:
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

    # dummy log with only 'days' activities
    dummy_log = create_dummy_log(year, week, year_week_department=year_week_department, columns=act.columns)
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

    # compute real fitness
    alignment_res = {}
    for key in act_alignment_res.keys():
      alignment_res[key] = get_real_fitness(act_alignment_res[key], dummy_alignment_res[key])

    results[year_week_department] = alignment_res

  # save results to json file
  with open(os.path.join(output_path, output_filename), 'w') as f:
    json.dump(results, f, indent=2)
