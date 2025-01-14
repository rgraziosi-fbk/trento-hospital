import pandas as pd

# Prepares DataFrame of the dataset
# Deep copy it, cast activity column to string and timestamp column to datetime, and sort rows by timestamp
# Returns the newly prepared Dataframe
def prepare_df(df, activity_key='ID_PAZ_DATA', timestamp_key='DATA'):
  df = df.copy(deep=True)
  
  df[activity_key] = df[activity_key].astype(str)
  df[timestamp_key] = pd.to_datetime(df[timestamp_key], format='%d/%m/%Y')
  df = df.sort_values(by=timestamp_key)

  return df