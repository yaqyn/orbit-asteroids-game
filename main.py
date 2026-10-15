"""Keyboard-first arcade entry point with deterministic verification options."""

import argparse
import os
import random
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from display import Display
from game import Game
from ui import Renderer


def positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pilot an upgradeable starfighter through a 3D-shaded asteroid field"
    )
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument(
        "--reduced-motion",
        action="store_true",
        help="Disable particles, star parallax, and asteroid rotation",
    )
    parser.add_argument("--seed", type=int, help="Deterministic random seed")
    parser.add_argument(
        "--frames", type=positive_int, help="Exit after N frames (verification)"
    )
    parser.add_argument("--screenshot", type=Path, help="Save the final rendered frame")
    parser.add_argument("--start", action="store_true", help="Skip the title screen")
    parser.add_argument(
        "--no-save", action="store_true", help="Keep best scores in memory only"
    )
    args = parser.parse_args(argv)
    if args.seed is not None:
        random.seed(args.seed)
    pygame.display.init()
    pygame.font.init()
    try:
        display = Display(args.fullscreen)
        screen = display.canvas
        pygame.display.set_caption("Orbit | Dodge / Split / Evolve")
        clock = pygame.time.Clock()
        game = Game(reduced_motion=args.reduced_motion, save_scores=not args.no_save)
        if args.start:
            game.reset()
        renderer = Renderer()
        running, frames = True, 0
        while running:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    display.toggle()
                    continue
                if not game.handle_event(event):
                    running = False
            if not running:
                break
            game.update(dt)
            renderer.draw(screen, game)
            display.present()
            frames += 1
            if args.frames and frames >= args.frames:
                break
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(display.screen, str(args.screenshot))
        game.save_best()
        return 0
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
