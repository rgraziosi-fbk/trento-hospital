import pandas as pd
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils

from config import YEAR_WEEK_DEPARTMENT_KEY, ACTIVITY_KEY, TIMESTAMP_KEY, RESERVE_KEY
from utils import prepare_df


def build_petri_net_for_week_department(plans, year_week_department, should_consider_reserves=True):
  # get operations for that specific week and department
  ops = plans[plans[YEAR_WEEK_DEPARTMENT_KEY] == year_week_department]
  ops = prepare_df(ops, activity_key=ACTIVITY_KEY, timestamp_key=TIMESTAMP_KEY)

  dates = ops[TIMESTAMP_KEY].unique()

  if len(dates) == 0:
    return None, None, None

  net = PetriNet(year_week_department)

  # sources contains the starting places of the net
  sources = []

  # at time t, current_reserves contains operations that can be executed at time t or t+1
  current_reserves = []

  # pointer to the previous day transition
  prev_day_t = None

  # for each day
  for day_idx, date in enumerate(dates):
    # get operations for that specific day
    ops_date = ops[ops[TIMESTAMP_KEY] == date]

    # create a black transition to indicate a day has passed
    next_day_t = PetriNet.Transition(f'day-{day_idx}')
    net.transitions.add(next_day_t)

    # handle reserves
    if should_consider_reserves:
      for reserve in current_reserves:
        petri_utils.add_arc_from_to(reserve, next_day_t, net)
      current_reserves = []

    # for each operation in that day
    for _, op_date in ops_date.iterrows():
      is_reserve = op_date[RESERVE_KEY] == 1

      p1 = PetriNet.Place(f'{date}-{op_date[ACTIVITY_KEY]}-1')
      p2 = PetriNet.Place(f'{date}-{op_date[ACTIVITY_KEY]}-2')

      if day_idx == 0:
        sources.append(p1)

      t = PetriNet.Transition(op_date[ACTIVITY_KEY], op_date[ACTIVITY_KEY])

      net.places.add(p1)
      net.places.add(p2)
      net.transitions.add(t)

      if prev_day_t:
        petri_utils.add_arc_from_to(prev_day_t, p1, net)  

      petri_utils.add_arc_from_to(p1, t, net)
      petri_utils.add_arc_from_to(t, p2, net)

      if should_consider_reserves and is_reserve:
        current_reserves.append(p2) # p2 must be linked to next_day_t on next iteration
      else:
        petri_utils.add_arc_from_to(p2, next_day_t, net)

    prev_day_t = next_day_t

  sink = PetriNet.Place('sink')
  net.places.add(sink)
  petri_utils.add_arc_from_to(prev_day_t, sink, net)

  if should_consider_reserves:
    # if some reserves are left, link them to sink
    for reserve in current_reserves:
      petri_utils.add_arc_from_to(reserve, next_day_t, net)
    current_reserves = []

  # insert initial tokens
  im = Marking()
  for source in sources:
    im[source] = 1

  fm = Marking()
  fm[sink] = 1

  return net, im, fm