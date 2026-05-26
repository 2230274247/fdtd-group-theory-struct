# -*- coding: utf-8 -*-
import argparse
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preview", "test", "full"], default="preview")
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--sleep", type=float, default=0.7)
    args = parser.parse_args()

    print("[SIM] mode=%s" % args.mode, flush=True)
    for idx in range(1, args.steps + 1):
        print("[SIM OUT] [%d/%d] running sample ..." % (idx, args.steps), flush=True)
        if idx == 3:
            print("[SIM ERR] warning: fake warning for stderr stream", file=sys.stderr, flush=True)
        time.sleep(args.sleep)
    print("[SIM] finished", flush=True)


if __name__ == "__main__":
    main()
