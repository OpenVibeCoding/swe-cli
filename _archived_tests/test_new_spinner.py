#!/usr/bin/env python3
"""Demo the new Orbital Animation spinner with fancy verbs."""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.ui.animations import Spinner
from rich.console import Console

# Same 102 fancy verbs from REPL
THINKING_VERBS = [
    "Thinking", "Processing", "Analyzing", "Computing", "Synthesizing",
    "Orchestrating", "Crafting", "Brewing", "Composing", "Contemplating",
    "Formulating", "Strategizing", "Architecting", "Designing", "Manifesting",
    "Conjuring", "Weaving", "Pondering", "Calculating", "Deliberating",
    "Ruminating", "Meditating", "Scheming", "Envisioning", "Imagining",
    "Conceptualizing", "Ideating", "Brainstorming", "Innovating", "Engineering",
    "Assembling", "Constructing", "Building", "Forging", "Molding",
    "Sculpting", "Fashioning", "Shaping", "Rendering", "Materializing",
    "Realizing", "Actualizing", "Executing", "Implementing", "Deploying",
    "Launching", "Initiating", "Activating", "Energizing", "Catalyzing",
    "Accelerating", "Optimizing", "Refining", "Polishing", "Perfecting",
    "Enhancing", "Augmenting", "Amplifying", "Boosting", "Elevating",
    "Transcending", "Transforming", "Evolving", "Adapting", "Morphing",
    "Mutating", "Iterating", "Recursing", "Traversing", "Navigating",
    "Exploring", "Discovering", "Uncovering", "Revealing", "Illuminating",
    "Deciphering", "Decoding", "Parsing", "Interpreting", "Translating",
    "Compiling", "Rendering", "Generating", "Producing", "Yielding",
    "Outputting", "Emitting", "Transmitting", "Broadcasting", "Propagating",
    "Disseminating", "Distributing", "Allocating", "Assigning", "Delegating",
    "Coordinating", "Synchronizing", "Harmonizing", "Balancing", "Calibrating",
    "Tuning", "Adjusting",
]

def test_new_spinner():
    """Test the new Orbital Animation spinner with fancy verbs."""
    console = Console()
    spinner = Spinner(console)

    console.print("\n╔════════════════════════════════════════════════════════════╗")
    console.print("║  [bold yellow]NEW FANCY SPINNER:[/bold yellow] Orbital Animation (Braille)    ║")
    console.print("║  [dim]Smooth orbital motion + 102 random fancy verbs[/dim]       ║")
    console.print("╚════════════════════════════════════════════════════════════╝\n")

    # Demo 10 random fancy verbs with the new spinner
    for i in range(10):
        thinking_verb = random.choice(THINKING_VERBS)
        console.print(f"[bold cyan]Demo #{i+1}:[/bold cyan]")

        # Show spinner with random verb
        spinner.start(f"{thinking_verb}...")
        time.sleep(2.0)
        spinner.stop()

        # Show completion
        console.print(f"⏺ {thinking_verb} complete!\n")

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("\n[bold]✨ New Spinner Features:[/bold]")
    console.print("  [cyan]•[/cyan] Orbital Animation - smooth circular motion")
    console.print("  [cyan]•[/cyan] Braille characters for professional look")
    console.print("  [cyan]•[/cyan] 102 random fancy verbs for variety")
    console.print("  [cyan]•[/cyan] Never boring - always fresh and engaging!")
    console.print()

if __name__ == "__main__":
    test_new_spinner()
