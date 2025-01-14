import pandas as pd
from datetime import date, timedelta

# Prepares DataFrame of the dataset
# Deep copy it, cast activity column to string and timestamp column to datetime, and sort rows by timestamp
# Returns the newly prepared Dataframe
def prepare_df(df, activity_key='ID_PAZ_DATA', timestamp_key='DATA'):
  df = df.copy(deep=True)
  
  df[activity_key] = df[activity_key].astype(str)
  df[timestamp_key] = pd.to_datetime(df[timestamp_key], format='%d/%m/%Y')
  df = df.sort_values(by=timestamp_key)

  return df


# Given year and week, returns a list of the days of that week for that year
# (Weeks start on Sundays)
def get_days_of_year_week(year, week):
  # Get the first day of the year
  first_day_of_year = date(year, 1, 1)

  # Get the day of the week for the first day of the year (0=Monday, 6=Sunday)
  day_of_week = first_day_of_year.weekday()

  # Calculate the first Sunday of the year
  first_sunday = first_day_of_year + timedelta(days=(6 - day_of_week if day_of_week != 6 else 0))

  # Count the first week of the year even if it does not contain a Sunday
  week_offset = 0 if first_day_of_year == first_sunday else 1

  # Calculate the first day of the given week
  start_of_week = first_sunday + timedelta(weeks=week - 1 - week_offset)

  # Return all days of the specified week and year (days within a week that goes beyond or before specified year are discarded)
  return [(start_of_week + timedelta(days=i)).isoformat() for i in range(7) if (start_of_week + timedelta(days=i)).year == year]
