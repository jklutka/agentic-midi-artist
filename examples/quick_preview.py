"""Example: Quick-start script to generate a single MIDI and launch Zenith preview."""

from pathlib import Path

from midi_app.patterns import create_waterfall
from midi_app.zenith import launch_zenith_preview

OUTPUT = Path("output/quick_demo.mid")


def main():
    print("Generating a waterfall MIDI...")
    create_waterfall(OUTPUT, num_notes=300, tempo_bpm=160, density=1.5)
    print(f"Saved: {OUTPUT}")

    print("Launching Zenith-MIDI preview...")
    try:
        proc = launch_zenith_preview(OUTPUT)
        print(f"Zenith launched (PID: {proc.pid})")
    except FileNotFoundError as e:
        print(f"\n{e}")
        print("\nTo use this script, download Zenith-MIDI and set ZENITH_MIDI_PATH.")


if __name__ == "__main__":
    main()
