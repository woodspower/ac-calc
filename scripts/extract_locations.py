#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
import srsly
import typer


# References:
# https://www.aircanada.com/


def main(
    locations_file: Path = typer.Argument("/project/ac_data/location.json", help="Locations data file."),
    output_file: Optional[Path] = typer.Argument(None),
):
    pass


if __name__ == "__main__":
    typer.run(main)
