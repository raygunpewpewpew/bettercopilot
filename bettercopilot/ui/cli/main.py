"""Command-line interface for BetterCopilot.

Provides a simple `ai` command with subcommands: ask, fix, rom, log.
"""
import argparse
import sys
from .commands import ask as ask_cmd, fix as fix_cmd, rom as rom_cmd, log as log_cmd


def build_parser():
    p = argparse.ArgumentParser(prog='ai')
    p.add_argument('--trace', action='store_true', help='Enable trace logging (JSONL)')
    sub = p.add_subparsers(dest='cmd')

    p_ask = sub.add_parser('ask')
    p_ask.add_argument('question', nargs='+')

    p_fix = sub.add_parser('fix')
    p_fix.add_argument('path')

    p_rom = sub.add_parser('rom')
    p_rom.add_argument('action', choices=['analyze'])
    p_rom.add_argument('rom_path')

    p_log = sub.add_parser('log')
    p_log.add_argument('--tail', action='store_true')

    return p


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    # Enable trace logging if requested
    if getattr(args, 'trace', False):
        try:
            from ...logging import enable_trace
            enable_trace(True)
        except Exception:
            pass

    if args.cmd == 'ask':
        question = ' '.join(args.question)
        ask_cmd.run(question)
    elif args.cmd == 'fix':
        fix_cmd.run(args.path)
    elif args.cmd == 'rom':
        rom_cmd.run(args.action, args.rom_path)
    elif args.cmd == 'log':
        log_cmd.run(tail=args.tail)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
