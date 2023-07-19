import typer
import os
import csv
from pathlib import Path
from rich import print

app = typer.Typer(no_args_is_help=True)


@app.command("scrape")
def run_scraper(
    input_file: Path = typer.Argument(..., help="The csv for input", file_okay=True, dir_okay=False, exists=True),
    column: str = typer.Option("property_id", help="The column for property IDs"),
    overwrite: bool = typer.Option(False, help="Overwrite existing database"),
):
    """Scrape data from BCAD website"""
    from bexar_scraper.data.scraper import get_scraped_data_schema, scrape
    from bexar_scraper.data.database import build_database, insert_record, clear_database

    if overwrite and os.path.exists("bexar_data.db"):
        clear_database()
    data_schema = get_scraped_data_schema()
    build_database(data_schema)
    property_ids = []
    with open(input_file, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            property_ids.append(int(row[column]))
    scraped_data = scrape(property_ids)
    for property_info in scraped_data:
        insert_record(property_info)
    print(
        f"\n[green bold]Success! [cyan bold]{len(scraped_data)}[/cyan bold] [green bold]records inserted into database\n"
    )


@app.command("clear")
def run_clear():
    """Clear scraped data"""
    from bexar_scraper.data.database import clear_database

    clear_database()


@app.command("frontend")
def run_frontend():
    """Run the frontend"""
    raise NotImplementedError("No implementation for running frontend yet")


if __name__ == "__main__":
    app()
