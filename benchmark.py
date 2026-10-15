"""Reproducible renderer stress test, independent of combat and frame pacing."""

import argparse
import json
import os
import random
import statistics
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--rocks", type=int, default=80)
    parser.add_argument("--frames", type=int, default=240)
    args = parser.parse_args()
    if args.rocks < 1 or args.frames < 1:
        parser.error("rocks and frames must be positive")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    from asteroid import Asteroid
    from constants import SCREEN_HEIGHT, SCREEN_WIDTH
    from game import Game
    from ui import Renderer

    pygame.display.init()
    pygame.font.init()
    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        random.seed(7)
        game, renderer = Game(save_scores=False), Renderer()
        game.reset()
        for _ in range(args.rocks):
            rock = Asteroid(
                random.randint(0, SCREEN_WIDTH),
                random.randint(100, 680),
                random.choice([20, 40, 60]),
            )
            rock.velocity.update(10, 10)
        samples = []
        for _ in range(args.frames):
            pygame.event.pump()
            for rock in game.asteroids:
                rock.update(1 / 60)
            start = time.perf_counter()
            renderer.draw(screen, game)
            samples.append((time.perf_counter() - start) * 1000)
        print(
            json.dumps(
                {
                    "rocks": args.rocks,
                    "frames": args.frames,
                    "driver": pygame.display.get_driver(),
                    "mean_ms": round(statistics.mean(samples), 2),
                    "p95_ms": round(
                        sorted(samples)[
                            min(len(samples) - 1, int(len(samples) * 0.95))
                        ],
                        2,
                    ),
                }
            )
        )
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
