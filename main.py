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


def lives_count(value):
    result = positive_int(value)
    if result > 9:
        raise argparse.ArgumentTypeError("must be between 1 and 9")
    return result


def frame_rate(value):
    result = positive_int(value)
    if result > 240:
        raise argparse.ArgumentTypeError("must be between 1 and 240")
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
    parser.add_argument("--lives", type=lives_count, default=3, help="Starting hull lives (1-9)")
    parser.add_argument("--fps", type=frame_rate, default=60, help="Frame-rate cap (1-240)")
    parser.add_argument(
        "--score-file", type=Path, help="Use a custom best-score file"
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
        game = Game(
            save_path=args.score_file,
            reduced_motion=args.reduced_motion,
            save_scores=not args.no_save,
            starting_lives=args.lives,
        )
        if args.start:
            game.reset()
        renderer = Renderer()
        running, frames = True, 0
        while running:
            dt = clock.tick(args.fps) / 1000
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
