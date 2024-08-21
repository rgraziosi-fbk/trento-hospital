import os
import matplotlib.pyplot as plt
import json

from config import *

# Calcolo fitness media per reparto
def compute_average_fitness_by_department(
  dataset,
  output_path='output',
  output_filename='average_fitness_by_department.json',
  input_filename='results.json',
):
  print('Computing average fitness by department...')
  
  with open(os.path.join(output_path, input_filename)) as f:
    results = json.load(f)

  departments = dataset[YEAR_WEEK_DEPARTMENT_KEY].unique().tolist()
  departments = [department.split('-')[2] for department in departments]
  departments = list(set(departments))
  departments = sorted(departments)

  results_by_department = { department: [] for department in departments }
  avg_fitness_by_department = {}

  for k, v in results.items():
    k_dep = k.split('-')[2]
    results_by_department[k_dep].append(v['average_trace_fitness'])

  for k, v in results_by_department.items():
    if len(v) == 0:
      avg_fitness = 0
      print(f'{k}: no fitness computed.')
    else:
      avg_fitness = sum(v) / len(v)
      print(f'{k}: avg fitness {(avg_fitness*100):.1f}%, perfect fitness {v.count(1.0)}/{len(v)}')

    avg_fitness_by_department[k] = avg_fitness

  for department, avg_fitness_department in zip(departments, avg_fitness_by_department.keys()):
    assert department == avg_fitness_department

  with open(os.path.join(output_path, output_filename), 'w') as f:
    json.dump(avg_fitness_by_department, f, indent=2)

  
def plot_average_fitness_by_department(
  dataset,
  output_path='output',
  output_filename='average_fitness_by_department.png',
  input_filenames=['average_fitness_by_department.json'],
):
  departments = dataset[YEAR_WEEK_DEPARTMENT_KEY].unique().tolist()
  departments = [department.split('-')[2] for department in departments]
  departments = list(set(departments))
  departments = sorted(departments)

  plt.figure(figsize=(10, 6))
  colors = ['skyblue', 'lightgreen', 'lightcoral', 'lightsalmon', 'lightpink']
  alpha = 1 if len(input_filenames) == 0 else 0.5

  for i, input_filename in enumerate(input_filenames):
    with open(os.path.join(output_path, input_filename)) as f:
      avg_fitness_by_department = json.load(f)
  
    # add possible missing departments
    for department in departments:
      if department not in avg_fitness_by_department:
        avg_fitness_by_department[department] = 0

    bars = plt.bar(departments, avg_fitness_by_department.values(), color=colors[i % len(colors)], alpha=alpha, label=input_filename)
    
    # for i, bar in enumerate(bars):
    #   plt.text(bar.get_x() + bar.get_width()/2, 0, f'{len(list(results_by_department.values())[i])}', ha='center', va='bottom')

  plt.xlabel('Departments')
  plt.ylabel('Average Fitness')
  plt.title('Average Fitness by Department')
  plt.legend(title='Input Files', bbox_to_anchor=(1.2, 1), loc='lower right', borderaxespad=0.)
  plt.xticks(rotation=90)

  # plt.text(0.5, 0.95, 'Inside bars are the number of weeks available for that department, i.e. the number of weeks on which fitness has been computed', ha='center', va='center', transform=plt.gcf().transFigure, fontsize=10, color='gray')
  
  plt.tight_layout()
  plt.savefig(os.path.join(output_path, output_filename))