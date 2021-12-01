#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
import srsly
import typer


# References:
# https://www.aircanada.com/ca/en/aco/home/aeroplan/earn/air-canada.html
# https://www.aircanada.com/ca/en/aco/home/aeroplan/partners.html


def main(
    partners_file: Path = typer.Argument("/project/ac_data/airline-en.json", help="Airline partners data file."),
    output_file: Optional[Path] = typer.Argument("/project/ac_calc/airlines/partners.json"),
):
    airline_partners = srsly.read_json(partners_file)

    if not ("details" in airline_partners and "partners" in airline_partners):
        raise ValueError("The partners file is missing details and partners keys.")

    # For each partner, determine if it's possible to earn Aeroplan miles, status qualifying
    # miles (SQM), and the earning rate by class of service and booking classes. BeautifulSoup
    # is used to parse the data table.
    parsed_partners = []
    for partner in airline_partners["partners"]:
        eligible_flights_tab = next(filter(lambda tab: tab["id"] == "1", partner["tabs"]))

        if eligibility_text := next(filter(lambda section: section["id"] == "1", eligible_flights_tab["sections"]), {}).get("content"):
            earns_app = "can earn Aeroplan points" in eligibility_text
            earns_sqm = (
                "Status Qualifying Miles" in eligibility_text
                and not "do not earn Status Qualifying Miles" in eligibility_text
            )
        else:
            earns_app, earns_sqm = False, False

        if earnings_text := next(filter(lambda section: section["id"] == "2", eligible_flights_tab["sections"]), {}).get("content"):
            soup = BeautifulSoup(earnings_text, "html5lib")

            header_row = soup.find("tr")
            headers = [th.text.strip() for th in soup.find("tr").find_all("th")]

            num_headers = len(headers)

            earning_rates = defaultdict(lambda: defaultdict(dict))
            region, cos = "*", "*"

            detail_rows = header_row.find_next_siblings("tr")
            for tr in detail_rows:
                if tds := tr.find_all(lambda t: t.name == "td" and "tablet-visible" not in t.attrs.get("class")):
                    if len(tds) > 4 or len(tds) < 2:
                        continue

                    if len(tds) == 4:
                        region = tds[0].text.strip("§*¥ \n")
                    if len(tds) >= 3:
                        cos = tds[-3].text.strip("§*¥ \n")

                    try:
                        rate = float(tds[-1].text.strip("% \n")) / 100.0
                    except:
                        rate = 0.0
                    rates = {
                        c.strip(): rate
                        for c in tds[-2].text.split(",")
                        if len(c.strip()) == 1  # Ignore special conditions
                    }

                    earning_rates[region][cos].update(rates)
        else:
            earning_rates = None

        parsed_partners.append({
            "id": partner["id"],
            "name": partner["name"],
            "region": partner["region"],
            "website": partner["website"],
            "logo": partner["logo"],
            "star_alliance_member": partner.get("group") == "Star alliance member",
            "codeshare_partner": partner.get("groupCompany") == "Air Canada codeshare partner",
            "earns_app": earns_app,
            "earns_sqm": earns_sqm,
            "earning_rates": earning_rates,
        })

    if output_file:
        srsly.write_json(output_file, parsed_partners)

    return parsed_partners


if __name__ == "__main__":
    typer.run(main)
