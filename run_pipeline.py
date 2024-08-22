import os
from datetime import datetime
import pandas as pd

from config import *
from compute_alignment import compute_alignment
from analyze_results import compute_average_fitness_by_department, plot_average_fitness_by_department

# Create an output folder for this specific pipeline run
timestamp = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
run_output_path = os.path.join(OUTPUT_PATH, timestamp)
os.makedirs(run_output_path)

# Load the dataset
dataset = pd.read_csv(DATASET_PATH, sep=DATASET_SEP, encoding=DATASET_ENCODING)

# for period, name in zip(['COVID', 'POST_COVID'], ['covid', 'post_covid']):
# for urgency_types_to_consider, name in zip([['Elezione'], ['Elezione', 'Urgenza', 'Emergenza']], ['e', 'eue']):
for should_consider_reserves, name in zip([True, False], ['reserves', 'noreserves']):
  print(f'Considering case "{name}"...')

  # Compute alignments
  compute_alignment(
    dataset=dataset,
    output_path=run_output_path,
    output_filename=f'results_{name}.json',
    urgency_types_to_consider=['Elezione', 'Urgenza', 'Emergenza'],
    should_consider_reserves=should_consider_reserves,
    should_save_petri_nets=True,
  )

  # Compute average fitness by department
  compute_average_fitness_by_department(
    dataset=dataset,
    output_path=run_output_path,
    output_filename=f'average_fitness_by_department_{name}.json',
    input_filename=f'results_{name}.json',
  )

# Plot average fitness by department
plot_average_fitness_by_department(
  dataset=dataset,
  output_path=run_output_path,
  input_filenames=[
    'average_fitness_by_department_reserves.json',
    'average_fitness_by_department_noreserves.json',
  ]
)