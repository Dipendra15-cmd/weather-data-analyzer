import argparse
import json
import sys
import time
from typing import Optional, Tuple, List, Dict

import requests

# Constants
GEOCODE_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_JSON_OUTPUT = "weather_output.json"
DEFAULT_CSV_OUTPUT = "weather_output.csv"
REQUEST_TIMEOUT_SECONDS = 10
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.5


def read_city_names_from_file(file_path: str) -> List[str]:
    """Reads city names from a file. Note: City name should be on a separate line"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            cities = [line.strip() for line in file if line.strip()]

        if not cities:
            print(
                f"[warning] The file '{file_path}' was read, but no cities were found.",
                file=sys.stderr
            )
        return cities
    except FileNotFoundError:
        print(f"[error] Could not find file: {file_path}", file=sys.stderr)
        raise
    except Exception as e:
        print(
            f"[error] Unexpected error reading the file '{file_path}': {e}",
            file=sys.stderr
        )
        raise


def fetch_data_with_retries(
    url: str, params: dict, retries: int = RETRY_ATTEMPTS
) -> Optional[dict]:
    """For HTTP requests"""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as err:
            if attempt < retries:
                print(
                    f"[info] Request failed (attempt {attempt}): {err}. Retrying...",
                    file=sys.stderr
                )
                time.sleep(RETRY_DELAY)
            else:
                print(
                    f"[error] Failed after {attempt} retries: {err}",
                    file=sys.stderr
                )
                return None


def get_city_coordinates(city_name: str) -> Optional[Tuple[float, float, str]]:
    """
    Fetches latitude and longitude for a given city name.
    Returns a tuple (latitude, longitude, city_name) if successful, or None if not.
    """
    params = {"name": city_name, "count": 1}
    response_data = fetch_data_with_retries(GEOCODE_API_URL, params)

    if not response_data:
        return None

    results = response_data.get("results")
    if not results:
        print(
            f"[warning] geocoding data not found for '{city_name}'.",
            file=sys.stderr
        )
        return None

    city_info = results[0]
    lat, lon = city_info.get("latitude"), city_info.get("longitude")
    city_name_from_api = city_info.get("name") or city_name

    if lat is None or lon is None:
        print(
            f"[warning] Error in geocoding data for city '{city_name}'",
            file=sys.stderr
        )
        return None

    return lat, lon, city_name_from_api


def get_current_weather_for_coordinates(lat: float, lon: float) -> Optional[
    dict]:
    """
    Fetches data using the OpenMeteo API for the current weather.
    Returns the data if successful, or None if not.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True
    }
    weather_data = fetch_data_with_retries(WEATHER_API_URL, params)

    if not weather_data:
        return None

    current_weather = weather_data.get("current_weather")
    if not current_weather:
        print(
            f"[warning] No current weather data found for coordinates {lat}, {lon}.",
            file=sys.stderr
        )
        return None

    return {
        "temperature": current_weather.get("temperature"),
        "windspeed": current_weather.get("windspeed"),
        "winddirection": current_weather.get("winddirection"),
        "weathercode": current_weather.get("weathercode"),
        "timestamp": current_weather.get("time"),
    }


def compute_weather_stats(temperatures: List[float]) -> Dict[
    str, Optional[float]]:
    """Computes basic stats (min, max, average) for a list of temperatures."""
    if not temperatures:
        return {"min": None, "max": None, "average": None}

    min_temp = min(temperatures)
    max_temp = max(temperatures)
    avg_temp = sum(temperatures) / len(temperatures)
    return {"min": min_temp, "max": max_temp, "average": avg_temp}


def save_to_json(file_path: str, data: dict) -> None:
    """Saves the given data to a JSON file with proper formatting."""
    try:
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        print(f"[info] Data successfully saved to {file_path}")
    except Exception as e:
        print(
            f"[error] Failed to save data to {file_path}: {e}", file=sys.stderr
        )

def print_weather_summary(data: dict) -> None:
    if not data:
        print("[info] No data to display.")
        return

    print("\n--- Weather Summary ---")
    temperatures = []
    for city, weather_info in data.items():
        if city == "stats":
            continue
        temp = weather_info.get("temperature")
        temperatures.append(temp if temp is not None else float("nan"))
        print(
            f"{city:20}  Temp: {temp}°C  Wind Speed: {weather_info.get('windspeed')} km/h  Time: {weather_info.get('timestamp')}"
        )

    stats = data.get("stats")
    if stats:
        print("\nStatistics:")
        print(f"  Max Temp: {stats.get('max')}°C")
        print(f"  Min Temp: {stats.get('min')}°C")
        print(
            f"  Avg Temp: {stats.get('average'):.2f}°C" if stats.get(
                "average"
            ) else "  Avg Temp: n/a"
        )
    print("------------------------\n")


def process_weather_for_cities(
    cities: List[str], output_format: str = "json",
    output_file: Optional[str] = None
) -> dict:
    weather_results = {}
    temperatures = []

    for city in cities:
        print(f"[info] Fetching data for {city}...")
        coordinates = get_city_coordinates(city)
        if not coordinates:
            print(f"[warn] Skipping {city} due to geocoding issues.")
            continue
        lat, lon, city_name = coordinates

        weather = get_current_weather_for_coordinates(lat, lon)
        if not weather:
            print(f"[warn] No weather data available for {city}.")
            continue

        weather_results[city_name] = {
            "temperature": weather["temperature"],
            "windspeed": weather["windspeed"],
            "winddirection": weather["winddirection"],
            "timestamp": weather["timestamp"]
        }

        if weather["temperature"] is not None:
            temperatures.append(weather["temperature"])

        time.sleep(0.5)

    stats = compute_weather_stats(temperatures)
    weather_results["stats"] = stats

    if output_format == "json":
        save_to_json(output_file or DEFAULT_JSON_OUTPUT, weather_results)
    else:
        save_to_csv(output_file or DEFAULT_CSV_OUTPUT, weather_results)

    print_weather_summary(weather_results)
    return weather_results


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Weather Data Fetcher and Analyzer"
    )
    parser.add_argument("file", help="Path to the file containing city names")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="json",
        help="Output format: JSON or CSV"
    )
    parser.add_argument(
        "--out",
        help="Path to the output file (defaults to 'weather_output.json' or 'weather_output.csv')"
    )
    return parser.parse_args(argv)


def main(argv: List[str] = None) -> int:
    args = parse_arguments(argv or sys.argv[1:])
    try:
        cities = read_city_names_from_file(args.file)
    except Exception as e:
        return 2

    if not cities:
        print("[error] Please add city names to the file", file=sys.stderr)
        return 3

    try:
        process_weather_for_cities(
            cities, output_format=args.format, output_file=args.out
        )
    except Exception as e:
        print(f"[error] Something went wrong: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
