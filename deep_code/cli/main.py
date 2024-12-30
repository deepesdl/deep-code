import click

from deep_code.cli.publish import publish_product


@click.group()
def main():
    """Deep Code CLI."""
    pass


main.add_command(publish_product)
if __name__ == "__main__":
    main()
