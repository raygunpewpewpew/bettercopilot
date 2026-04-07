"""`ai log` command (minimal): prints basic logs or tails them.
"""
import time


def run(tail: bool = False):
    if tail:
        print('Tailing logs (ctrl-c to stop)')
        try:
            while True:
                print('[log] heartbeat')
                time.sleep(1)
        except KeyboardInterrupt:
            print('Stopped')
    else:
        print('Recent logs:')
        print('[log] started BetterCopilot CLI')
        print('[log] orchestator idle')
