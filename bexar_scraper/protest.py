import typer
import os
from rich import print

app = typer.Typer(no_args_is_help=True)

@app.command("scrape")
def run_scraper(overwrite: bool = typer.Option(False, help="Overwrite existing database")):
    """Scrape data from BCAD website"""
    from bexar_scraper.data.scraper import get_scraped_data_schema, scrape
    from bexar_scraper.data.database import build_database, insert_record, clear_database

    if overwrite and os.path.exists("bexar_data.db"):
        clear_database()
    data_schema = get_scraped_data_schema()
    build_database(data_schema)
    scraped_data = scrape(list(range(400000, 400100)))
    for property_info in scraped_data:
        insert_record(property_info)
    print(f"\n[green bold]Success! [cyan bold]{len(scraped_data)}[/cyan bold] [green bold]records inserted into database\n")

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