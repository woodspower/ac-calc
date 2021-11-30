#!/usr/bin/env python

import codecs
from collections import defaultdict
import csv
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
import srsly
import typer


# References:
# https://www.aircanada.com/


def main(
    locations_file: Path = typer.Argument("/project/ac_data/location.json", help="Locations data file."),
    airports_file: Path = typer.Argument("/project/ac_calc/locations/airports.csv"),
    country_continents_file: Path = typer.Argument("/project/ac_calc/locations/country_continents.csv"),
    output_file: Optional[Path] = typer.Argument("/project/ac_calc/locations/airports.json"),
):
    location_data = srsly.read_json(locations_file)

    with open(airports_file) as f:
        reader = csv.reader(f)
        assert(next(reader) == ["airport_code", "country", "latitude", "longitude"])
        airports_data = {
            row[0]: (row[1], float(row[2]), float(row[3]))
            for row in reader
        }

    with open(country_continents_file) as f:
        reader = csv.reader(f)
        assert(next(reader) == ["country", "continent"])
        country_continents_data = {
            row[0]: row[1]
            for row in reader
        }

    # Prepare reverse lookups for groups and markets.
    groups_by_country = {}
    for group in location_data["groups"]:
        for country in group["countries"]:
            groups_by_country[country] = group["code"]

    markets_by_country = {}
    for market in location_data["markets"]:
        for country in market["countries"]:
            markets_by_country[country] = market["code"]

    # Extract airports, noting the countries and cities they're in.
    airports = []
    airport_codes = set()
    for country in location_data["countries"]:
        states = country.get("states", [country])
        for state in states:
            for city in state["cities"]:
                for airport in city["airports"]:
                    airport_data = airports_data.get(airport["code"])
                    if not airport_data:
                        print(f"No data for {airport['code']}.")
                        airport_data = ("", 0, 0)
                    elif not airport_data[0] == country["name"]:
                        print(f"Differing countries for {airport['code']}: {airport_data[0]} | {country['name']}")

                    airports.append({
                        "airport": codecs.decode(airport["name"], "unicode-escape").strip(),
                        "airport_code": airport["code"],
                        "latitude": airport_data[1],
                        "longitude": airport_data[2],
                        "continent": country_continents_data.get(country["name"].strip()) or country_continents_data.get(airport_data[0]),
                        "country": codecs.decode(country["name"], "unicode-escape").strip(),
                        "country_code": country["code"],
                        **({
                            "state": codecs.decode(state["name"], "unicode-escape").strip(),
                            "state_code": state["code"],
                        } if state is not country else {}),
                        "city": codecs.decode(city["name"], "unicode-escape").strip(),
                        "city_code": city["code"],
                        "group": groups_by_country.get(country["code"], None),
                        "market": markets_by_country.get(country["code"], "INT"),
                        "nearby": [
                            nearby_airport["code"]
                            for nearby_airport in airport.get("nearbyAirports", [])
                        ],
                    })
                    airport_codes.add(airport["code"])

    # Add entries for airports that exist in airports.csv but not Air Canada data.
    for airport_code, airport_data in airports_data.items():
        if airport_code not in airport_codes:
            airports.append({
                "airport": airport_code,
                "airport_code": airport_code,
                "latitude": airport_data[1],
                "longitude": airport_data[2],
                "continent": country_continents_data.get(airport_data[0]),
                "country": airport_data[0],
            })

    if output_file:
        srsly.write_json(output_file, airports)


if __name__ == "__main__":
    typer.run(main)
