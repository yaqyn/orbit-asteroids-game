import math
import random

import pygame

from circleshape import CircleShape
from constants import (
    ASTEROID_MIN_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from logger import log_event

# Reuse material shades instead of rebuilding color tuples for every face.
ROCK_COLORS = [
    tuple(
        int(lo + (hi - lo) * i / 255) for lo, hi in zip((42, 39, 65), (250, 148, 132))
    )
    for i in range(256)
]
ROCK_EDGES = [tuple(max(0, channel - 12) for channel in color) for color in ROCK_COLORS]
LIGHT = pygame.Vector3(-0.5, -0.7, 1).normalize()


class Asteroid(CircleShape):
    def __init__(self, x: float, y: float, radius: float) -> None:
        super().__init__(x, y, radius)
        # Local randomness keeps decorative geometry out of gameplay RNG.
        rng = random.Random(f"{x}:{y}:{radius}")
        self.spin = rng.uniform(-0.6, 0.6)
        self.angle = rng.uniform(0, math.tau)
        phi = (1 + math.sqrt(5)) / 2
        vertices = [
            (-1, phi, 0),
            (1, phi, 0),
            (-1, -phi, 0),
            (1, -phi, 0),
            (0, -1, phi),
            (0, 1, phi),
            (0, -1, -phi),
            (0, 1, -phi),
            (phi, 0, -1),
            (phi, 0, 1),
            (-phi, 0, -1),
            (-phi, 0, 1),
        ]
        self.mesh = [
            pygame.Vector3(v).normalize() * radius * rng.uniform(0.88, 1.08)
            for v in vertices
        ]
        self.faces = [
            (0, 11, 5),
            (0, 5, 1),
            (0, 1, 7),
            (0, 7, 10),
            (0, 10, 11),
            (1, 5, 9),
            (5, 11, 4),
            (11, 10, 2),
            (10, 7, 6),
            (7, 1, 8),
            (3, 9, 4),
            (3, 4, 2),
            (3, 2, 6),
            (3, 6, 8),
            (3, 8, 9),
            (4, 9, 5),
            (2, 4, 11),
            (6, 2, 10),
            (8, 6, 7),
            (9, 8, 1),
        ]
        # Small fragments need a silhouette, not subpixel triangle detail.
        if radius > 40:
            midpoints = {}

            def midpoint(i, j):
                key = tuple(sorted((i, j)))
                if key not in midpoints:
                    vertex = (
                        (self.mesh[i] + self.mesh[j]).normalize()
                        * radius
                        * rng.uniform(0.82, 1.04)
                    )
                    midpoints[key] = len(self.mesh)
                    self.mesh.append(vertex)
                return midpoints[key]

            refined = []
            for a, b, c in self.faces:
                ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
                refined.extend([(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)])
            self.faces = refined
        self.reduced_motion = False
        self._image = None
        self._image_angle = None

    def draw(self, screen):
        extent = math.ceil(self.radius * 1.1) + 2
        rect = pygame.Rect(0, 0, extent * 2, extent * 2)
        rect.center = (round(self.position.x), round(self.position.y))
        if not screen.get_rect().colliderect(rect):
            return
        # Small angle changes share a raster. Translation is still smooth each frame;
        # mesh transforms, lighting, and polygon rasterization run only as needed.
        angle = round(self.angle / 0.04) * 0.04
        if self._image is None or angle != self._image_angle:
            self._image = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()
            self._rasterize(self._image, angle, extent)
            self._image_angle = angle
        screen.blit(self._image, rect)

    def _rasterize(self, screen, angle, extent):
        # Rotate a low-poly 3D mesh, light surface normals, then project to 2D.
        # Collision stays circular so the course physics remain predictable.
        vertices = [
            v.rotate_y_rad(angle).rotate_x(24).rotate_z_rad(angle * 0.4)
            for v in self.mesh
        ]
        visible = []
        for i, j, k in self.faces:
            a, b, c = vertices[i], vertices[j], vertices[k]
            normal = (b - a).cross(c - a).normalize()
            if normal.z <= 0:
                continue
            shade = max(0, min(255, int(normal.dot(LIGHT) * 255)))
            points = [
                (extent + a.x, extent + a.y),
                (extent + b.x, extent + b.y),
                (extent + c.x, extent + c.y),
            ]
            visible.append((a.z + b.z + c.z, shade, points))
        visible.sort(key=lambda face: face[0])
        for _, shade, points in visible:
            pygame.draw.polygon(screen, ROCK_COLORS[shade], points)
            pygame.draw.polygon(screen, ROCK_EDGES[shade], points, 1)

    def update(self, dt):
        self.position += self.velocity * dt
        if not self.reduced_motion:
            self.angle += self.spin * dt
        margin = self.radius * 3
        if not (
            -margin <= self.position.x <= SCREEN_WIDTH + margin
            and -margin <= self.position.y <= SCREEN_HEIGHT + margin
        ):
            self.kill()

    def split(self):
        self.kill()

        if self.radius <= ASTEROID_MIN_RADIUS:
            return
        log_event("asteroid_split")
        angle = random.uniform(20, 50)
        velocity1 = self.velocity.rotate(angle)
        velocity2 = self.velocity.rotate(-angle)
        new_radius = self.radius - ASTEROID_MIN_RADIUS
        asteroid1 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid1.velocity = velocity1 * 1.2

        asteroid2 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid2.velocity = velocity2 * 1.2
