import os
from datetime import datetime
import pandas as pd

from config import *
from compute_alignment import compute_alignment
from analyze_results import compute_average_fitness_by_department

# Create an output folder for this specific pipeline run
timestamp = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
run_output_path = os.path.join(OUTPUT_PATH, timestamp)
os.makedirs(run_output_path)

# Load the dataset
dataset = pd.read_csv(DATASET_PATH, sep=DATASET_SEP, encoding=DATASET_ENCODING)

# Compute alignments
compute_alignment(
  dataset=dataset,
  output_path=run_output_path,
  urgency_types_to_consider=['Elezione', 'Urgenza', 'Emergenza'],
  should_save_petri_nets=True,
)

# Compute average fitness by department
compute_average_fitness_by_department(
  dataset=dataset,
  output_path=run_output_path
)