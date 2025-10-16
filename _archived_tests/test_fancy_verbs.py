#!/usr/bin/env python3
"""Demo the fancy verb rotation during thinking."""

import random
import sys
import time
from pathlib import Path

# Add opencli to path
sys.path.insert(0, str(Path(__file__).parent))

from opencli.ui.animations import Spinner
from rich.console import Console

# Same list as in REPL (100 verbs!)
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

def test_fancy_verbs():
    """Test the fancy verb rotation."""
    console = Console()
    spinner = Spinner(console)

    console.print("\n[bold]Testing Fancy Verb Rotation[/bold]\n")
    console.print("[dim]Each API call shows a different random verb![/dim]\n")

    for i in range(15):
        thinking_verb = random.choice(THINKING_VERBS)
        console.print(f"\n[bold cyan]Simulated API Call #{i+1}:[/bold cyan]")

        # Start spinner with random verb
        spinner.start(f"{thinking_verb}...")

        # Simulate API call
        time.sleep(1.5)

        # Stop spinner
        spinner.stop()

        console.print(f"[green]✓[/green] Used verb: [yellow]{thinking_verb}[/yellow]")

    console.print("\n[bold green]Demo Complete![/bold green]")
    console.print(f"\nTotal unique verbs available: [cyan]{len(THINKING_VERBS)}[/cyan]")
    console.print("Each API call randomly selects a verb - never boring!\n")

if __name__ == "__main__":
    test_fancy_verbs()
