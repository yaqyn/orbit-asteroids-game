import pygame

from circleshape import CircleShape
from constants import (
    ACCENT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHOT_LIFETIME_SECONDS,
    SHOT_RADIUS,
)


class Shot(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, SHOT_RADIUS)
        self.lifetime = SHOT_LIFETIME_SECONDS

    def draw(self, screen):
        direction = (
            self.velocity.normalize()
            if self.velocity.length()
            else pygame.Vector2(0, -1)
        )
        pygame.draw.line(
            screen, (40, 91, 118), self.position - direction * 23, self.position, 6
        )
        pygame.draw.line(
            screen, ACCENT, self.position - direction * 14, self.position, 2
        )
        pygame.draw.circle(screen, (246, 232, 200), self.position, 2)

    def update(self, dt):
        self.position += self.velocity * dt
        self.lifetime -= dt
        if self.lifetime <= 0 or not (
            0 <= self.position.x <= SCREEN_WIDTH
            and 0 <= self.position.y <= SCREEN_HEIGHT
        ):
            self.kill()
