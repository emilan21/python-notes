import typer

from .output import app as output_app

app = typer.Typer()

app.add_typer(output_app, name="output")

if __name__ == "__main__":
    app()
