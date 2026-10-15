"""Present a fixed game canvas safely on any desktop or window size."""

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH


class Display:
    def __init__(self, fullscreen=False):
        self.fullscreen = fullscreen
        self.window_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.scaled = None
        self.open()
        self.canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()

    def open(self):
        self.screen = pygame.display.set_mode(
            (0, 0) if self.fullscreen else self.window_size,
            pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE,
        )
        self.scaled = None

    def toggle(self):
        if not self.fullscreen:
            self.window_size = self.screen.get_size()
        self.fullscreen = not self.fullscreen
        self.open()

    def present(self):
        # Never draw world coordinates onto a larger, uncleared desktop surface.
        # A separate canvas also clips offscreen rocks before scaling.
        width, height = self.screen.get_size()
        scale = min(width / SCREEN_WIDTH, height / SCREEN_HEIGHT)
        size = (max(1, int(SCREEN_WIDTH * scale)), max(1, int(SCREEN_HEIGHT * scale)))
        target = pygame.Rect((0, 0), size)
        target.center = self.screen.get_rect().center
        self.screen.fill((0, 0, 0))
        if size == self.canvas.get_size():
            self.screen.blit(self.canvas, target)
        else:
            if self.scaled is None or self.scaled.get_size() != size:
                self.scaled = pygame.Surface(size).convert()
            pygame.transform.scale(self.canvas, size, self.scaled)
            self.screen.blit(self.scaled, target)
        pygame.display.flip()
