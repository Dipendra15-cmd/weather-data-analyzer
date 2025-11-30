# Weather Data Analyzer

This is a Python command-line tool which reads a list of city from the text file and fetches their current temperatures using the Open-Meteo API. And after fetching current temperature of cities, it saves the result in "weather_data.csv" file.

## Features

* Reads the city names from `cities.txt` (City name should be on one line)
* Fetches current temperature for each city using OpenMeteo API
* Calculates max, average and min temperature
* Saves everything in a clean csv file named weather_data.csv

## How to Run

1. Create a virtual environment:
   ```
   python3 -m venv env
   ```
2. Install the required packages
   ```
   pip install -r requirements.txt
   ```
3. Add your cities (one per line) into `cities.txt`
4. Run the program:

   ```
   python weather.py cities.py
   ```

## Output

* Individual temperatures of the cities
* Highest, lowest, and average
* Saved automatically to `output.json`
* 
