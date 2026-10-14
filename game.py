"""Gameplay state and transitions independent of the window loop."""

import json
import os
import random
import tempfile
from pathlib import Path

import pygame
from asteroid import Asteroid
from asteroidfield import AsteroidField
from player import Player
from shot import Shot
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_LIVES, RESPAWN_SECONDS


def score_path():
    # Keep the original storage location to preserve scores after the Orbit rename.
    return (
        Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        / "asteroids/best.json"
    )


class Game:
    def __init__(self, save_path=None, reduced_motion=False, save_scores=True):
        self.save_path = Path(save_path) if save_path is not None else score_path()
        self.reduced_motion = reduced_motion
        self.save_scores = save_scores
        self.best = self.load_best()
        self.persisted_best = self.best
        self.save_error = False
        self.reset()
        self.state = "title"

    def load_best(self):
        try:
            value = json.loads(self.save_path.read_text(encoding="utf-8"))["best"]
            return value if type(value) is int and value >= 0 else 0
        except (OSError, ValueError, TypeError, KeyError):
            return 0

    def save_best(self):
        self.best = max(self.best, self.score)
        if not self.save_scores or self.best <= self.persisted_best:
            return
        temporary = None
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                             dir=self.save_path.parent,
                                             prefix=f".{self.save_path.name}.", delete=False) as file:
                temporary = Path(file.name)
                json.dump({"best": self.best}, file)
            temporary.replace(self.save_path)
            self.save_error = False
            self.persisted_best = self.best
        except OSError:
            self.save_error = True
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    self.save_error = True

    def reset(self):
        self.asteroids, self.shots = pygame.sprite.Group(), pygame.sprite.Group()
        self.updatable, self.drawable = pygame.sprite.Group(), pygame.sprite.Group()
        Player.containers = (self.updatable, self.drawable)
        Asteroid.containers = (self.asteroids, self.updatable, self.drawable)
        Shot.containers = (self.shots, self.updatable, self.drawable)
        AsteroidField.containers = self.updatable
        self.player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.field = AsteroidField()
        self.score, self.elapsed, self.lives = 0, 0, PLAYER_LIVES
        self.invulnerable = RESPAWN_SECONDS
        self.particles = []
        self.state = "playing"

    @property
    def level(self):
        return 1 + int(self.elapsed // 20)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.save_best()
            return False
        if event.type == pygame.WINDOWFOCUSLOST and self.state == "playing":
            self.state = "paused"
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            self.save_best()
            return False
        if event.key in {pygame.K_RETURN, pygame.K_r} and self.state in {
            "title",
            "game_over",
        }:
            self.reset()
        elif event.key in {pygame.K_p, pygame.K_RETURN} and self.state in {
            "playing",
            "paused",
        }:
            self.state = "paused" if self.state == "playing" else "playing"
        return True

    def burst(self, position, count=18):
        if self.reduced_motion:
            return
        for _ in range(count):
            self.particles.append(
                [
                    pygame.Vector2(position),
                    pygame.Vector2(random.uniform(40, 160), 0).rotate(
                        random.uniform(0, 360)
                    ),
                    random.uniform(0.2, 0.6),
                ]
            )

    def hit_player(self):
        if self.invulnerable > 0 or self.state != "playing":
            return
        self.burst(self.player.position, 30)
        self.lives -= 1
        if self.lives <= 0:
            self.state = "game_over"
            self.save_best()
        else:
            self.player.position.update(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            self.player.rotation = 0
            self.invulnerable = RESPAWN_SECONDS

    def update(self, dt):
        if self.state != "playing":
            return
        dt = min(max(dt, 0), 0.05)
        self.elapsed += dt
        self.invulnerable = max(0, self.invulnerable - dt)
        self.field.difficulty = min(2.8, 1 + (self.level - 1) * 0.15)
        self.updatable.update(dt)
        for asteroid in list(self.asteroids):
            for shot in list(self.shots):
                if shot.collides_with(asteroid):
                    self.score += {20: 100, 40: 50, 60: 20}.get(asteroid.radius, 20)
                    self.burst(asteroid.position)
                    shot.kill()
                    asteroid.split()
                    break
            if asteroid.alive() and asteroid.collides_with(self.player):
                self.hit_player()
                if self.state == "game_over":
                    break
        for particle in self.particles:
            particle[0] += particle[1] * dt
            particle[2] -= dt
        self.particles = [particle for particle in self.particles if particle[2] > 0][
            -300:
        ]
