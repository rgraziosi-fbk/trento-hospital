from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils

from utils import prepare_df, get_days_of_year_week

# Given the full log of planned operations as a dataframe and a specific year-week-department
# Builds and returns the petri net of that specific week and department
def build_petri_net_for_week(
  plans,
  year_week_department,
  year_week_department_key='Year_Week_Reparto',
  activity_key='concept:name',
  timestamp_key='time:timestamp',
):
  year, week = int(year_week_department.split('-')[0]), int(year_week_department.split('-')[1])
  dates = get_days_of_year_week(year, week)

  # get operations only of specific department, year and week
  ops = plans[plans[year_week_department_key] == year_week_department]
  ops = prepare_df(ops, activity_key=activity_key, timestamp_key=timestamp_key)

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
    ops_date = ops[ops[timestamp_key] == date]

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
      p1 = PetriNet.Place(f'{date}-{op_date[activity_key]}-1')
      p2 = PetriNet.Place(f'{date}-{op_date[activity_key]}-2')

      prev_day_ps.append(p2)

      t = PetriNet.Transition(op_date[activity_key], f'{op_date[activity_key]}')

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