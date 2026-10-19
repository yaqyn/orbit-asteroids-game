"""Gameplay state and transitions independent of the window loop."""

import json
import os
import random
import tempfile
from pathlib import Path

import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import PLAYER_LIVES, RESPAWN_SECONDS, SCREEN_HEIGHT, SCREEN_WIDTH
from player import Player
from progression import UPGRADES, Salvage
from shot import Shot


def score_path():
    # Keep the original storage location to preserve scores after the Orbit rename.
    return (
        Path(os.getenv("XDG_STATE_HOME") or str(Path.home() / ".local/state"))
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
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.save_path.parent,
                prefix=f".{self.save_path.name}.",
                delete=False,
            ) as file:
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
        self.fx_rng = random.Random(710)
        self.exhaust_timer = 0.0
        self.salvage = []
        self.collected = 0
        self.xp = 0
        self.rank = 1
        self.next_rank = 12
        self.modules = {key: 0 for key in UPGRADES}
        self.upgrade_choices = []
        self.shield_max = 50
        self.shield = 50.0
        self.shield_delay = 0.0
        self.kills = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.contract_target = 15
        self.contracts = 0
        self.notice = "Flight systems online. Break rocks; collect the mint salvage."
        self.notice_timer = 6.0
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
        if event.key == pygame.K_m:
            self.toggle_reduced_motion()
            return True
        if self.state == "upgrade":
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                index = event.key - pygame.K_1
                if index < len(self.upgrade_choices):
                    self.apply_upgrade(self.upgrade_choices[index])
            return True
        if event.key == pygame.K_r and self.state == "paused":
            self.reset()
            return True
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

    def toggle_reduced_motion(self):
        self.reduced_motion = not self.reduced_motion
        if self.reduced_motion:
            self.particles.clear()
        for rock in self.asteroids:
            rock.reduced_motion = self.reduced_motion

    def burst(self, position, count=18):
        if self.reduced_motion:
            return
        for _ in range(count):
            self.particles.append(
                [
                    pygame.Vector2(position),
                    pygame.Vector2(self.fx_rng.uniform(40, 220), 0).rotate(
                        self.fx_rng.uniform(0, 360)
                    ),
                    self.fx_rng.uniform(0.3, 0.8),
                ]
            )

    def hit_player(self):
        if self.invulnerable > 0 or self.state != "playing":
            return
        self.burst(self.player.position, 30)
        self.shield_delay = 6.0
        self.combo = 0
        if self.shield >= 25:
            self.shield -= 25
            self.invulnerable = 0.8
            self.notice, self.notice_timer = "Impact absorbed / shield -25", 2.5
            return
        self.shield = 0
        self.lives -= 1
        if self.lives <= 0:
            self.state = "game_over"
            self.save_best()
        else:
            self.player.position.update(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            self.player.rotation = 180
            self.player.velocity.update(0, 0)
            self.invulnerable = RESPAWN_SECONDS

    def update(self, dt):
        if self.state != "playing":
            return
        dt = min(max(dt, 0), 0.05)
        self.elapsed += dt
        self.invulnerable = max(0, self.invulnerable - dt)
        self.field.difficulty = min(2.8, 1 + (self.level - 1) * 0.15)
        for rock in self.asteroids:
            rock.reduced_motion = self.reduced_motion
        self.updatable.update(dt)
        self.shield_delay = max(0, self.shield_delay - dt)
        if self.shield_delay == 0:
            self.shield = min(self.shield_max, self.shield + 5 * dt)
        self.notice_timer = max(0, self.notice_timer - dt)
        self.combo_timer = max(0, self.combo_timer - dt)
        if self.combo_timer == 0:
            self.combo = 0
        self.update_exhaust(dt)
        for pickup in list(self.salvage):
            if pickup.update(dt, self.player, 115 + self.modules["magnet"] * 45):
                self.collected += pickup.value
                self.xp += pickup.value
                self.salvage.remove(pickup)
            elif pickup.life <= 0:
                self.salvage.remove(pickup)
        for asteroid in list(self.asteroids):
            for shot in list(self.shots):
                if shot.collides_with(asteroid):
                    self.combo += 1
                    self.combo_timer = 3.0
                    self.kills += 1
                    multiplier = 1 + min(4, self.combo // 5) * 0.25
                    self.score += int(
                        {20: 100, 40: 50, 60: 20}.get(asteroid.radius, 20) * multiplier
                    )
                    self.salvage.append(
                        Salvage(
                            asteroid.position,
                            asteroid.velocity,
                            int(asteroid.radius // 20),
                        )
                    )
                    self.salvage = self.salvage[-120:]
                    if self.kills >= self.contract_target:
                        self.contracts += 1
                        self.contract_target += 15 + self.contracts * 5
                        self.xp += 8
                        self.score += 500
                        self.notice, self.notice_timer = (
                            "Contract complete / +500 score / +8 salvage XP",
                            4.0,
                        )
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
        self.check_rank()

    def update_exhaust(self, dt):
        if self.reduced_motion or not self.player.thrust:
            return
        self.exhaust_timer += dt
        while self.exhaust_timer >= 0.012:
            self.exhaust_timer -= 0.012
            direction = self.player.forward * self.player.thrust
            for side in (-1, 1):
                position = (
                    self.player.position
                    - direction * 19
                    + direction.rotate(90) * side * 8
                )
                velocity = (
                    -direction.rotate(self.fx_rng.uniform(-12, 12))
                    * self.fx_rng.uniform(90, 240)
                    + self.player.velocity * 0.2
                )
                self.particles.append(
                    [position, velocity, self.fx_rng.uniform(0.25, 0.55), "engine"]
                )

    def check_rank(self):
        if self.xp < self.next_rank or self.state != "playing":
            return
        self.xp -= self.next_rank
        self.rank += 1
        self.next_rank = 12 + (self.rank - 1) * 6
        available = [
            key for key, (_, _, cap) in UPGRADES.items() if self.modules[key] < cap
        ]
        if not available:
            return
        # Stable rotation offers variety without consuming the spawn RNG.
        offset = (self.rank - 2) % len(available)
        self.upgrade_choices = (available[offset:] + available[:offset])[:3]
        self.state = "upgrade"

    def apply_upgrade(self, key):
        if self.state != "upgrade" or key not in self.upgrade_choices:
            return
        self.modules[key] += 1
        if key == "cannon":
            self.player.weapon_level += 1
        elif key == "engine":
            self.player.engine_level += 1
        elif key == "shield":
            self.shield_max += 25
            self.shield = float(self.shield_max)
        elif key == "spread":
            self.player.multishot = True
        elif key == "repair":
            self.lives = min(PLAYER_LIVES, self.lives + 1)
            self.shield = float(self.shield_max)
        self.notice, self.notice_timer = UPGRADES[key][0] + " installed", 3.0
        self.state = "playing"
        self.check_rank()
