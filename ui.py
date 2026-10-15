"""Cover-inspired navigation display and shared keyboard menus."""

import math
import random
from functools import lru_cache

import pygame

from constants import (
    ACCENT,
    BACKGROUND,
    CYAN,
    DANGER,
    FOREGROUND,
    MUTED,
    PANEL,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from progression import UPGRADES


class Renderer:
    def __init__(self):
        self.display_font = pygame.font.Font(None, 108)
        self.heading_font = pygame.font.Font(None, 64)
        self.body_font = pygame.font.Font(None, 29)
        self.utility_font = pygame.font.Font(pygame.font.match_font("monospace"), 17)
        self.small_font = pygame.font.Font(pygame.font.match_font("monospace"), 14)
        self.hud_panel = pygame.Surface(
            (SCREEN_WIDTH, 96), pygame.SRCALPHA
        ).convert_alpha()
        self.hud_panel.fill((16, 23, 41, 240))
        self.overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        ).convert_alpha()
        self.overlay.fill((12, 18, 33, 225))
        rng = random.Random(31)
        self.stars = [
            (
                rng.randrange(SCREEN_WIDTH),
                rng.randrange(SCREEN_HEIGHT),
                rng.uniform(0.15, 1),
                rng.uniform(0, math.tau),
            )
            for _ in range(230)
        ]
        self.backdrop = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.backdrop.fill(BACKGROUND)
        # Static dust band is cached, rather than generating thousands of dots per frame.
        for _ in range(5200):
            x = rng.randrange(SCREEN_WIDTH)
            y = int(500 - x * 0.24 + rng.gauss(0, 72))
            if 0 <= y < SCREEN_HEIGHT:
                self.backdrop.set_at(
                    (x, y), rng.choice([(27, 33, 53), (31, 35, 58), (37, 37, 61)])
                )

    @staticmethod
    @lru_cache(maxsize=256)
    def rendered_text(font, text, color):
        return font.render(text, True, color)

    def text(self, screen, text, position, color=FOREGROUND, font=None, center=False):
        surface = self.rendered_text(font or self.body_font, text, color)
        screen.blit(
            surface,
            surface.get_rect(center=position)
            if center
            else surface.get_rect(topleft=position),
        )

    def bar(self, screen, x, y, width, value, maximum, color):
        pygame.draw.rect(screen, (43, 48, 69), (x, y, width, 5))
        pygame.draw.rect(
            screen, color, (x, y, int(width * max(0, min(1, value / maximum))), 5)
        )

    def background(self, screen, game):
        screen.blit(self.backdrop, (0, 0))
        distance = pygame.Vector2() if game.reduced_motion else game.player.distance
        velocity = pygame.Vector2() if game.reduced_motion else game.player.velocity
        for x, y, depth, phase in self.stars:
            pos = pygame.Vector2(
                (x - distance.x * depth * 0.38) % SCREEN_WIDTH,
                (y - distance.y * depth * 0.38) % SCREEN_HEIGHT,
            )
            intensity = int(
                90
                + 110 * depth
                + (
                    0
                    if game.reduced_motion
                    else 18 * math.sin(game.elapsed * 0.7 + phase)
                )
            )
            color = (intensity, intensity, min(255, intensity + 20))
            tail = velocity * depth * (0.055 if game.player.boosting else 0.012)
            if tail.length() > 2:
                pygame.draw.line(screen, (49, 83, 106), pos, pos + tail, 1)
            pygame.draw.circle(screen, color, pos, 1 if depth < 0.85 else 2)
        # Quiet orbit-chart geometry from the illustrated cover.
        for radius in (170, 260, 350):
            pygame.draw.circle(screen, (34, 42, 62), (1090, 210), radius, 1)
        pygame.draw.line(screen, (34, 42, 62), (1090, 95), (1090, 560), 1)

    def draw(self, screen, game):
        self.background(screen, game)
        for particle in game.particles:
            position, velocity, life = particle[:3]
            engine = len(particle) > 3
            color = (65, 155, 217) if engine else (167, 104, 128)
            end = position - velocity * 0.035
            pygame.draw.line(
                screen, color, end, position, max(1, int(life * (7 if engine else 4)))
            )
            pygame.draw.circle(
                screen, CYAN if engine else DANGER, position, max(1, int(life * 3))
            )
        for pickup in game.salvage:
            x, y = pickup.position
            pygame.draw.circle(screen, (32, 65, 70), (x, y), 9, 1)
            pygame.draw.polygon(
                screen, ACCENT, [(x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)], 1
            )
        for sprite in game.drawable:
            if sprite is game.player and game.state == "title":
                continue
            sprite.draw(screen)
        if game.invulnerable > 0 and game.state != "title":
            pygame.draw.circle(screen, ACCENT, game.player.position, 32, 1)
        elif game.shield >= 25 and game.state == "playing":
            pos = game.player.position
            pygame.draw.arc(
                screen, (66, 119, 143), (pos.x - 30, pos.y - 30, 60, 60), -2.6, -0.5, 2
            )
        self.hud(screen, game)
        if game.state != "playing":
            self.menu(screen, game)

    def hud(self, screen, game):
        screen.blit(self.hud_panel, (0, 0))
        pygame.draw.line(screen, (65, 77, 97), (32, 95), (1248, 95))
        self.text(screen, "ORBIT / FLIGHT TELEMETRY", (32, 17), ACCENT, self.small_font)
        self.text(screen, f"{game.score:07d}", (32, 40), FOREGROUND, self.body_font)
        self.text(
            screen,
            f"Best {max(game.best, game.score):,}",
            (32, 72),
            MUTED,
            self.small_font,
        )
        self.text(
            screen,
            f"Hull  {' / '.join(['I'] * game.lives) or 'LOST'}",
            (278, 18),
            FOREGROUND,
            self.utility_font,
        )
        self.text(
            screen,
            f"Shield  {int(game.shield):03d}/{game.shield_max}",
            (278, 45),
            CYAN,
            self.small_font,
        )
        self.bar(screen, 278, 76, 180, game.shield, game.shield_max, CYAN)
        self.text(
            screen, f"Pilot rank {game.rank:02d}", (510, 18), ACCENT, self.utility_font
        )
        self.text(
            screen,
            f"Salvage XP  {game.xp}/{game.next_rank}",
            (510, 45),
            MUTED,
            self.small_font,
        )
        self.bar(screen, 510, 76, 180, game.xp, game.next_rank, ACCENT)
        self.text(
            screen,
            f"Ion charge {int(game.player.energy):03d}%",
            (744, 18),
            CYAN,
            self.utility_font,
        )
        self.text(
            screen,
            f"Speed {int(game.player.velocity.length()):03d}  /  {'BOOST' if game.player.boosting else 'CRUISE'}",
            (744, 45),
            MUTED,
            self.small_font,
        )
        self.bar(screen, 744, 76, 180, game.player.energy, 100, CYAN)
        self.text(
            screen,
            f"Sector {game.level:02d} / {int(game.elapsed) // 60:02d}:{int(game.elapsed) % 60:02d}",
            (976, 18),
            FOREGROUND,
            self.utility_font,
        )
        self.text(
            screen,
            f"Chain {game.combo:02d}  x{1 + min(4, game.combo // 5) * 0.25:.2f}",
            (976, 48),
            DANGER,
            self.utility_font,
        )
        # Radar shows actual relative asteroid positions, not decorative contacts.
        pygame.draw.circle(screen, (43, 56, 76), (1177, 565), 54, 1)
        pygame.draw.line(screen, (43, 56, 76), (1123, 565), (1231, 565))
        pygame.draw.line(screen, (43, 56, 76), (1177, 511), (1177, 619))
        for rock in game.asteroids:
            delta = (rock.position - game.player.position) * 0.075
            if delta.length() < 50:
                pygame.draw.circle(screen, DANGER, pygame.Vector2(1177, 565) + delta, 2)
        pygame.draw.circle(screen, ACCENT, (1177, 565), 3)
        self.text(screen, "Local scan", (1135, 627), MUTED, self.small_font)
        self.text(
            screen,
            f"Contract / clear {game.contract_target} rocks   {game.kills}/{game.contract_target}",
            (32, 598),
            FOREGROUND,
            self.small_font,
        )
        self.bar(screen, 32, 624, 285, game.kills, game.contract_target, DANGER)
        modules = [
            f"{UPGRADES[key][0]} {value}"
            for key, value in game.modules.items()
            if value and key != "repair"
        ]
        self.text(
            screen,
            " / ".join(modules[:3]) or "Modules / stock flight systems",
            (32, 641),
            MUTED,
            self.small_font,
        )
        if game.notice_timer > 0:
            self.text(screen, game.notice, (640, 121), ACCENT, self.small_font, True)
        pygame.draw.rect(screen, PANEL, (0, 679, SCREEN_WIDTH, 41))
        self.text(
            screen,
            "WASD / arrows  fly     SPACE  fire     SHIFT  boost     P  pause   F11  fullscreen   ESC  quit",
            (32, 691),
            MUTED,
            self.utility_font,
        )

    def menu(self, screen, game):
        screen.blit(self.overlay, (0, 0))
        if game.state == "upgrade":
            self.text(
                screen,
                f"Pilot rank {game.rank:02d} / field refit",
                (640, 150),
                ACCENT,
                self.utility_font,
                True,
            )
            self.text(
                screen,
                "Choose your next module",
                (640, 214),
                FOREGROUND,
                self.heading_font,
                True,
            )
            self.text(
                screen,
                "Combat is frozen. Press 1, 2, or 3 to install and continue.",
                (640, 273),
                MUTED,
                center=True,
            )
            for i, key in enumerate(game.upgrade_choices):
                x = 64 + i * 391
                pygame.draw.rect(screen, PANEL, (x, 340, 370, 205))
                pygame.draw.line(screen, ACCENT, (x, 340), (x + 370, 340), 2)
                name, description, _cap = UPGRADES[key]
                self.text(
                    screen,
                    f"[{i + 1}]  Tier {game.modules[key] + 1}",
                    (x + 23, 365),
                    ACCENT,
                    self.utility_font,
                )
                self.text(screen, name, (x + 23, 410), FOREGROUND)
                # Fixed copy wrapping keeps each choice within its own column.
                words, line, y = description.split(), "", 456
                for word in words:
                    if len(line + word) > 29:
                        self.text(screen, line, (x + 23, y), MUTED, self.utility_font)
                        line, y = "", y + 25
                    line += word + " "
                self.text(screen, line, (x + 23, y), MUTED, self.utility_font)
            self.text(
                screen,
                "Upgrades last for this run. ESC exits.",
                (640, 603),
                MUTED,
                self.utility_font,
                True,
            )
            return
        self.text(
            screen,
            "DODGE / SPLIT / EVOLVE",
            (640, 190),
            ACCENT,
            self.utility_font,
            True,
        )
        title = {
            "title": "ORBIT",
            "paused": "FLIGHT PAUSED",
            "game_over": "SIGNAL LOST",
        }[game.state]
        self.text(screen, title, (640, 284), FOREGROUND, self.display_font, True)
        detail = {
            "title": "A lone pilot. A shifting field. Build a ship that survives.",
            "paused": "Flight, shields, salvage, and contracts are frozen.",
            "game_over": f"Score {game.score:,}  /  Rank {game.rank}  /  {game.kills} rocks  /  {game.contracts} contracts",
        }[game.state]
        self.text(screen, detail, (640, 376), MUTED, center=True)
        self.text(
            screen,
            "Collect salvage  /  choose modules  /  chain kills for bonus score",
            (640, 422),
            MUTED,
            self.utility_font,
            True,
        )
        action = {
            "title": "ENTER  launch",
            "paused": "ENTER / P  resume",
            "game_over": "ENTER / R  fly again",
        }[game.state]
        self.text(screen, action, (640, 497), ACCENT, self.body_font, True)
        self.text(
            screen,
            "WASD / arrows  fly    SPACE  fire    SHIFT  boost",
            (640, 571),
            FOREGROUND,
            self.utility_font,
            True,
        )
        self.text(
            screen,
            "P  pause    ESC  quit    /    Shield recharges after 6s without impact",
            (640, 610),
            MUTED,
            self.small_font,
            True,
        )
        if game.save_error:
            self.text(
                screen,
                "Best score could not be saved; this run is still available.",
                (640, 650),
                DANGER,
                center=True,
            )
