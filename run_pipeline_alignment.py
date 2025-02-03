import os
from datetime import datetime
import pandas as pd

from config import *
from compute_alignment import compute_alignment
from analyze_alignment_results import compute_average_fitness_for_week, plot_average_fitness_for_week, compute_average_fitness_for_department, plot_average_fitness_for_department

# Create an output folder for this specific pipeline run
timestamp = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
run_output_path = os.path.join(OUTPUT_PATH, timestamp)
os.makedirs(run_output_path)

# Load the dataset
dataset = pd.read_csv(DATASET_PATH, sep=DATASET_SEP, encoding=DATASET_ENCODING)

# for period, name in zip(['COVID', 'POST_COVID'], ['covid', 'post_covid']):
for urgency_types_to_consider, name in zip([['Elezione'], ['Elezione', 'Urgenza', 'Emergenza']], ['e', 'eue']):
# for should_consider_reserves, name in zip([True, False], ['reserves', 'noreserves']):
  print(f'Considering case "{name}"...')

  # Compute alignments
  compute_alignment(
    dataset=dataset,
    output_path=run_output_path,
    output_filename=f'results_{name}.json',
    urgency_types_to_consider=urgency_types_to_consider,
    should_consider_reserves=False,
    should_save_petri_nets=True,
  )

  # Compute average fitness for week across all departments
  compute_average_fitness_for_week(
    dataset=dataset,
    input_filename=f'results_{name}.json',
    output_path=run_output_path,
    output_filename=f'average_fitness_for_week_{name}.json',
  )

  # Compute average fitness for department across all weeks
  compute_average_fitness_for_department(
    dataset,
    input_filename=f'results_{name}.json',
    output_path=run_output_path,
    output_filename=f'average_fitness_for_department_{name}.json',
  )


# Plot average fitness for week across all departments
plot_average_fitness_for_week(
  dataset=dataset,
  input_filenames=[
    'average_fitness_for_week_e.json',
    'average_fitness_for_week_eue.json',
  ],
  output_path=run_output_path,
)

# Plot average fitness for department across all weeks
plot_average_fitness_for_department(
  dataset,
  input_filenames=[
    'average_fitness_for_department_e.json',
    'average_fitness_for_department_eue.json',
  ],
  output_path=run_output_path,
)