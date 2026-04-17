import typer

app = typer.Typer()

@app.command()
def output():
    print("Hello World")
