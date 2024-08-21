import os
import pm4py
import pandas as pd
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.conformance import fitness_alignments
import importlib.util
from tqdm import tqdm
import json

from config import *

def cast_df(df):
  df = df.copy()
  
  df[ACTIVITY_KEY] = df[ACTIVITY_KEY].astype(str)
  df[TIMESTAMP_KEY] = pd.to_datetime(df[TIMESTAMP_KEY], format='%d/%m/%Y')
  df = df.sort_values(by=TIMESTAMP_KEY)

  return df

def build_petri_net_for_week(prev, year_week_department):
  # ottieni operazioni solo per specifico anno, settimana e reparto
  ops = prev[prev[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department]

  # conversioni necessarie per evitare errori
  ops = cast_df(ops)

  # costruisci petri net delle operazioni preventivate per quello specifico reparto di quella specifica settimana
  # il dataframe passato per fare discovery è in pratica una sola traccia (infatti il case_id è Year_Week_Reparto e c'è un solo valore per esso)
  dates = ops[TIMESTAMP_KEY].unique()

  net = PetriNet(year_week_department)

  if len(dates) == 0:
    return None, None, None

  # sources conterrà i places di partenza (in cui verranno messi i token iniziali)
  sources = []
  prev_day_t = None

  # per ogni giorno
  for i, date in enumerate(dates):
    ops_date = ops[ops[TIMESTAMP_KEY] == date] # operazioni di quello specifico giorno

    next_day_t = PetriNet.Transition(f'day-{i}')
    net.transitions.add(next_day_t)

    # per ogni operazione di quel giorno
    for j, op_date in ops_date.iterrows():
      p1 = PetriNet.Place(f'{date}-{op_date[ACTIVITY_KEY]}-1')
      p2 = PetriNet.Place(f'{date}-{op_date[ACTIVITY_KEY]}-2')

      if i == 0:
        sources.append(p1)

      t = PetriNet.Transition(op_date[ACTIVITY_KEY], op_date[ACTIVITY_KEY])

      net.places.add(p1)
      net.places.add(p2)
      net.transitions.add(t)

      if prev_day_t:
        petri_utils.add_arc_from_to(prev_day_t, p1, net)  

      petri_utils.add_arc_from_to(p1, t, net)
      petri_utils.add_arc_from_to(t, p2, net)
      petri_utils.add_arc_from_to(p2, next_day_t, net)

    prev_day_t = next_day_t

  sink = PetriNet.Place('sink')
  net.places.add(sink)
  petri_utils.add_arc_from_to(prev_day_t, sink, net)

  # inserisci token iniziali
  im = Marking()
  for source in sources:
    im[source] = 1

  fm = Marking()
  fm[sink] = 1

  return net, im, fm

def compute_alignment(
  dataset,
  output_path='output',
  output_filename='results.json',
  urgency_types_to_consider=['Elezione'],
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

    # costruisci la petri net
    net, im, fm = build_petri_net_for_week(prev, year_week_department)

    if net == None:
      skipped.append(year_week_department)
      continue

    if should_save_petri_nets:
      petri_nets_path = os.path.join(output_path, 'petri_nets')
      if importlib.util.find_spec('graphviz'):
        if not os.path.exists(petri_nets_path):
          os.makedirs(petri_nets_path)
        
        pm4py.save_vis_petri_net(net, im, fm, os.path.join(petri_nets_path, f'{year_week_department}.svg'))

      # generate traces from petrinet
      # log = pm4py.play_out(net, im, fm)
      # pm4py.write_xes(log, f'{year_week_department}.xes')

    # filtra per year_week_department
    act = act[act[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department]

    # conversioni necessarie per evitare errori
    act = cast_df(act)

    # conformance checking
    alignment_res = fitness_alignments(
      act,
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
