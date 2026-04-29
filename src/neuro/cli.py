import click
from neuro.commands import init, status

@click.group()
def main():
    """Neuro CLI: Manage AI Agent skills and tools."""
    pass

@main.command()
@click.option('--force', is_flag=True, help='Force create directories')
def init_cmd(force):
    """Initialise Neuro skills for agents."""
    init.run(force=force)

@main.command()
def status_cmd():
    """Check active agent links."""
    status.run()

if __name__ == "__main__":
    main()
