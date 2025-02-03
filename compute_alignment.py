import os
import pm4py
from pm4py.conformance import fitness_alignments
import importlib.util
from tqdm import tqdm
import json

from config import *
from utils import prepare_df
from build_petri_net import build_petri_net_for_week_department

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
    # split dataset in planned and actual operations (plans and actuals)
    plans, actuals = dataset[dataset[SLICE_KEY] == SLICE_PLAN_VAL], dataset[dataset[SLICE_KEY] == SLICE_ACTUAL_VAL]

    # costruisci la petri net
    net, im, fm = build_petri_net_for_week_department(
      plans,
      year_week_department,
      should_consider_reserves=should_consider_reserves
    )

    if net == None:
      skipped.append(year_week_department)
      continue

    if should_save_petri_nets:
      petri_nets_path = os.path.join(output_path, 'petri_nets', '_'.join(urgency_types_to_consider))
      if importlib.util.find_spec('graphviz'):
        if not os.path.exists(petri_nets_path):
          os.makedirs(petri_nets_path)
        
        pm4py.save_vis_petri_net(net, im, fm, os.path.join(petri_nets_path, f'{year_week_department}-{should_consider_reserves}.svg'))

      # generate traces from petrinet
      # log = pm4py.play_out(net, im, fm)
      # pm4py.write_xes(log, f'{year_week_department}.xes')

    # get actual operations for that specific week and department
    actuals = actuals[actuals[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department]
    actuals = prepare_df(actuals, activity_key=ACTIVITY_KEY, timestamp_key=TIMESTAMP_KEY)

    # conformance checking
    alignment_res = fitness_alignments(
      actuals,
      net,
      im,
      fm,
      multi_processing=False,
      activity_key=ACTIVITY_KEY,
      case_id_key=YEAR_WEEK_DEPARTMENT_KEY,
      timestamp_key=TIMESTAMP_KEY,
    )

    results[year_week_department] = alignment_res

  # save results to json file
  with open(os.path.join(output_path, output_filename), 'w') as f:
    json.dump(results, f, indent=2)
