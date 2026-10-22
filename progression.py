"""Run-local salvage, pilot ranks, and meaningful module choices."""

import pygame

UPGRADES = {
    "cannon": ("Pulse accelerator", "Reduce fire delay 16% per tier.", 5),
    "engine": ("Ion drive", "Raise thrust and cruising speed.", 5),
    "shield": ("Shield capacitor", "+25 shield capacity; recharge now.", 4),
    "magnet": ("Salvage tractor", "+45 salvage attraction range.", 4),
    "spread": ("Trident array", "Fire three projectiles in a fan.", 1),
    "repair": (
        "Hull reconstruction",
        "Restore one hull life and shields.",
        float("inf"),
    ),
}


class Salvage:
    def __init__(self, position, velocity, value):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity) * 0.15
        self.value = value
        self.life = 14.0

    def update(self, dt, player, radius):
        self.life -= dt
        if self.life <= 0:
            return False
        delta = player.position - self.position
        if 0 < delta.length() < radius:
            self.velocity += delta.normalize() * 1100 * dt
        self.velocity *= 0.96 ** (dt * 60)
        self.position += self.velocity * dt
        return self.position.distance_to(player.position) < player.radius + 9
