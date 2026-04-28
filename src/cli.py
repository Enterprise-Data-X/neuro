# neuro/cli.py

import argparse
from .commands import init, audit, audit_run, tui

def main():
    parser = argparse.ArgumentParser(prog="neuro")
    subparsers = parser.add_subparsers(dest="command")

    # neuro init
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("path", nargs="?", default=".")

    # neuro audit
    subparsers.add_parser("audit")

    # neuro audit run
    audit_run_parser = subparsers.add_parser("audit-run")
    audit_run_parser.add_argument("file", nargs="?")

    # neuro tui
    tui_parser = subparsers.add_parser("tui")

    args = parser.parse_args()

    if args.command == "tui":
        tui.run()
    elif args.command == "init":
        init.run(args.path)
    elif args.command == "audit":
        audit.run()
    elif args.command == "audit-run":
        audit_run.run(args.file)
    else:
        parser.print_help()