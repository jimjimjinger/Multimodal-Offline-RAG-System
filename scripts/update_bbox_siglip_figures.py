"""Compatibility entry point for rebuilding the current IEEE figures."""

from build_ieee_figures import build


if __name__ == "__main__":
    for output in build():
        print(output)
