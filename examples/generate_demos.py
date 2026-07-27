"""Example: Generate various MIDI files for Zenith-MIDI visualization."""

from pathlib import Path

from midi_app.dense_song import create_dense_song
from midi_app.generator import create_chord_progression, create_scale
from midi_app.patterns import create_rainbow_spread, create_spiral, create_waterfall

OUTPUT_DIR = Path("output")


def main():
    print("Generating MIDI files for Zenith-MIDI visualization...\n")

    # Simple scale
    path = create_scale(OUTPUT_DIR / "c_major_scale.mid", root=60, scale_type="major")
    print(f"  Created: {path}")

    # Minor scale
    path = create_scale(OUTPUT_DIR / "a_minor_scale.mid", root=57, scale_type="minor")
    print(f"  Created: {path}")

    # Chord progression (I-V-vi-IV in C major)
    chords = [
        [60, 64, 67],       # C major
        [67, 71, 74],       # G major
        [69, 72, 76],       # A minor
        [65, 69, 72],       # F major
    ]
    path = create_chord_progression(OUTPUT_DIR / "chord_progression.mid", chords=chords)
    print(f"  Created: {path}")

    # Waterfall pattern (visually impressive)
    path = create_waterfall(OUTPUT_DIR / "waterfall.mid", num_notes=500, density=2.0)
    print(f"  Created: {path}")

    # Rainbow spread
    path = create_rainbow_spread(OUTPUT_DIR / "rainbow_spread.mid", num_waves=12)
    print(f"  Created: {path}")

    # Spiral pattern
    path = create_spiral(OUTPUT_DIR / "spiral.mid", revolutions=6)
    print(f"  Created: {path}")

    # Dense musical texture
    path = create_dense_song(OUTPUT_DIR / "dense_song.mid", bars=16, density=0.8, seed=42)
    print(f"  Created: {path}")

    print(f"\nAll files saved to: {OUTPUT_DIR.resolve()}")
    print("Open these in Zenith-MIDI to preview the visualizations!")


if __name__ == "__main__":
    main()
