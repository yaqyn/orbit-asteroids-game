"""Inertial flight, boost energy, and upgradeable cannons."""

import math

import pygame

from circleshape import CircleShape
from constants import (
    ACCENT,
    CYAN,
    FOREGROUND,
    PLAYER_RADIUS,
    PLAYER_SHOOT_COOLDOWN_SECONDS,
    PLAYER_SHOOT_SPEED,
    PLAYER_SPEED,
    PLAYER_TURN_SPEED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from shot import Shot


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.cooldown = 0
        self.rotation = 180
        self.thrust = 0
        self.boosting = False
        self.boost_locked = False
        self.energy = 100.0
        self.engine_level = 0
        self.weapon_level = 0
        self.multishot = False
        self.distance = pygame.Vector2()

    @property
    def forward(self):
        return pygame.Vector2(0, 1).rotate(self.rotation)

    def triangle(self):
        forward = self.forward
        right = forward.rotate(90) * self.radius / 1.5
        return [
            self.position + forward * self.radius,
            self.position - forward * self.radius - right,
            self.position - forward * self.radius + right,
        ]

    def draw(self, screen):
        if self.thrust:
            direction = self.forward * self.thrust
            for side in (-1, 1):
                nozzle = (
                    self.position - direction * 19 + direction.rotate(90) * side * 8
                )
                tip = nozzle - direction * (42 if self.boosting else 20)
                pygame.draw.line(screen, (34, 84, 145), nozzle, tip, 7)
                pygame.draw.line(screen, CYAN, nozzle, tip, 2)
                pygame.draw.circle(screen, FOREGROUND, nozzle, 2)
        nose, left, right = self.triangle()
        rear = self.position - self.forward * 10
        pygame.draw.polygon(screen, (27, 65, 83), [nose, left, rear, right])
        pygame.draw.polygon(screen, FOREGROUND, [nose, left, rear, right], 2)
        pygame.draw.line(screen, ACCENT, nose, rear, 2)
        pygame.draw.circle(screen, CYAN, self.position, 3)

    def rotate(self, dt):
        self.rotation = (self.rotation + PLAYER_TURN_SPEED * dt) % 360

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        keys = pygame.key.get_pressed()
        turn = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(
            keys[pygame.K_a] or keys[pygame.K_LEFT]
        )
        self.rotate(turn * dt)
        self.thrust = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(
            keys[pygame.K_s] or keys[pygame.K_DOWN]
        )
        boost_pressed = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if not boost_pressed:
            self.boost_locked = False
        if self.energy <= 5:
            self.boost_locked = True
        self.boosting = boost_pressed and self.thrust != 0 and not self.boost_locked
        self.energy = max(
            0, min(100, self.energy + (-34 if self.boosting else 20) * dt)
        )
        self.velocity += (
            self.forward
            * self.thrust
            * (620 + self.engine_level * 100)
            * (2.4 if self.boosting else 1)
            * dt
        )
        self.velocity *= math.exp(-1.7 * dt)
        limit = (300 + self.engine_level * 35) * (2 if self.boosting else 1)
        if self.velocity.length() > limit:
            self.velocity.scale_to_length(limit)
        movement = self.velocity * dt
        self.position += movement
        self.distance += movement
        if keys[pygame.K_SPACE]:
            self.shoot()
        self.position.x %= SCREEN_WIDTH
        self.position.y %= SCREEN_HEIGHT

    def move(self, dt):
        self.position += self.forward * PLAYER_SPEED * dt

    def shoot(self):
        if self.cooldown > 0:
            return
        self.cooldown = PLAYER_SHOOT_COOLDOWN_SECONDS * 0.84**self.weapon_level
        for angle in [-10, 0, 10] if self.multishot else [0]:
            muzzle = self.position + self.forward * self.radius
            shot = Shot(muzzle.x, muzzle.y)
            shot.velocity = (
                self.forward.rotate(angle) * PLAYER_SHOOT_SPEED + self.velocity * 0.4
            )
