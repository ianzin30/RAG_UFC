"""One entry point for retrieval experiments and saved-result diagnostics."""
import argparse
import importlib
import sys

COMMANDS = {
    'search': 'benchmark.search.run',
    'select': 'benchmark.selection.run',
    'report': 'benchmark.selection.report',
    'diagnose': 'benchmark.selection.diagnostic',
}


def main():
    parser = argparse.ArgumentParser(description='Current benchmark: original 70 questions, Cumbuco single-shot/adaptive retrieval.')
    parser.add_argument('command', choices=COMMANDS, help='search: compare retrieval policies; select/report/diagnose: saved-result utilities')
    args = parser.parse_args(sys.argv[1:2])
    sys.argv = [sys.argv[0], *sys.argv[2:]]
    importlib.import_module(COMMANDS[args.command]).main()


if __name__ == '__main__':
    main()
