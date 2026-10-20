import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from asteroid import Asteroid
from constants import SCREEN_WIDTH
from game import Game, score_path
from shot import Shot
from ui import Renderer


class GameTests(unittest.TestCase):
    def test_expired_salvage_cannot_award_xp_at_the_ship(self):
        from progression import Salvage
        pickup = Salvage(self.game.player.position, pygame.Vector2(), 3)
        pickup.life = 0.01
        self.game.salvage.append(pickup)
        self.game.update(0.02)
        self.assertEqual(self.game.xp, 0)
        self.assertEqual(self.game.collected, 0)
        self.assertEqual(self.game.salvage, [])

    def test_rank_after_all_upgrades_are_capped_keeps_playing(self):
        from game import UPGRADES
        game = Game(save_scores=False)
        game.reset()
        game.modules = {key: cap for key, (_, _, cap) in UPGRADES.items()}
        game.xp = game.next_rank
        game.check_rank()
        self.assertEqual(game.state, "playing")
        self.assertEqual(game.rank, 2)
        self.assertEqual(game.upgrade_choices, [])

    def test_empty_state_home_uses_home_directory(self):
        home = Path(tempfile.gettempdir()) / "asteroids-test-home"
        with (
            patch.dict(os.environ, {"XDG_STATE_HOME": ""}),
            patch.object(Path, "home", return_value=home),
        ):
            self.assertEqual(score_path(), home / ".local/state/asteroids/best.json")

    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((1280, 720))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.game = Game(Path(self.temp.name) / "best.json")
        self.game.reset()

    def key(self, key):
        return self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_title_pause_resume_restart_and_quit(self):
        self.game.state = "title"
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.state, "playing")
        self.key(pygame.K_p)
        self.game.update(0.05)
        self.assertEqual(self.game.elapsed, 0)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.state, "playing")
        self.game.state = "game_over"
        self.game.score = 100
        self.key(pygame.K_r)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertFalse(self.key(pygame.K_ESCAPE))

    def test_restart_from_pause_starts_a_fresh_run(self):
        self.game.score = 250
        self.game.state = "paused"
        self.key(pygame.K_r)
        self.assertEqual(self.game.state, "playing")
        self.assertEqual(self.game.score, 0)

    def test_lives_protection_and_best_score(self):
        self.game.score = 120
        self.game.hit_player()
        self.assertEqual(self.game.lives, 3)
        self.game.shield = 0
        for remaining in [2, 1, 0]:
            self.game.invulnerable = 0
            self.game.hit_player()
            self.assertEqual(self.game.lives, remaining)
        self.assertEqual(self.game.state, "game_over")
        self.assertEqual(Game(self.game.save_path).best, 120)

    def test_single_collision_scores_once(self):
        asteroid = Asteroid(200, 200, 20)
        Shot(200, 200)
        Shot(200, 200)
        self.game.update(0)
        self.assertEqual(self.game.score, 100)
        self.assertFalse(asteroid.alive())
        self.assertEqual(len(self.game.shots), 1)

    def test_splitting_asteroid(self):
        asteroid = Asteroid(200, 200, 60)
        asteroid.velocity.update(100, 0)
        with patch("asteroid.log_event"):
            asteroid.split()
        self.assertEqual(len(self.game.asteroids), 2)
        self.assertTrue(all(a.radius == 40 for a in self.game.asteroids))

    def test_shot_cooldown_and_expiration(self):
        self.game.player.shoot()
        self.game.player.shoot()
        self.assertEqual(len(self.game.shots), 1)
        next(iter(self.game.shots)).update(2)
        self.assertEqual(len(self.game.shots), 0)

    def test_player_wrap_and_offscreen_cleanup(self):
        self.game.player.position.x = SCREEN_WIDTH + 10
        self.game.player.update(0)
        self.assertEqual(self.game.player.position.x, 10)
        asteroid = Asteroid(-500, -500, 20)
        asteroid.update(0)
        self.assertFalse(asteroid.alive())

    def test_focus_loss_pauses(self):
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.game.state, "paused")

    def test_difficulty_and_delta_cap(self):
        self.game.elapsed = 100
        self.game.update(5)
        self.assertAlmostEqual(self.game.elapsed, 100.05)
        self.assertGreater(self.game.field.difficulty, 1)

    def test_reduced_motion(self):
        self.game.reduced_motion = True
        self.game.burst(pygame.Vector2(100, 100))
        self.assertEqual(self.game.particles, [])

    def test_reduced_motion_can_be_toggled_during_play(self):
        self.game.particles.append([pygame.Vector2(), pygame.Vector2(), 1])
        asteroid = Asteroid(100, 100, 20)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        self.assertTrue(self.game.reduced_motion)
        self.assertEqual(self.game.particles, [])
        self.assertTrue(asteroid.reduced_motion)
        self.assertEqual(self.game.notice, "Reduced motion on")
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        self.assertEqual(self.game.notice, "Reduced motion off")

    def test_corrupt_score_and_write_failure(self):
        self.game.save_path.write_text("[]")
        self.assertEqual(Game(self.game.save_path).best, 0)
        self.game.score = 10
        with patch(
            "game.tempfile.NamedTemporaryFile", side_effect=OSError("read-only")
        ):
            self.game.save_best()
        self.assertTrue(self.game.save_error)
        self.assertEqual(self.game.best, 10)
        self.game.save_best()
        self.assertFalse(self.game.save_error)
        self.assertEqual(Game(self.game.save_path).best, 10)

    def test_failed_score_replace_preserves_save_and_cleans_temporary(self):
        self.game.save_path.write_text('{"best": 5}')
        self.game.score = 10
        with patch.object(Path, "replace", side_effect=OSError("blocked")):
            self.game.save_best()
        self.assertTrue(self.game.save_error)
        self.assertEqual(self.game.save_path.read_text(), '{"best": 5}')
        self.assertEqual(
            list(self.game.save_path.parent.iterdir()), [self.game.save_path]
        )

    def test_render_all_states(self):
        renderer = Renderer()
        screen = pygame.display.get_surface()
        for state in ["title", "playing", "paused", "game_over", "upgrade"]:
            self.game.state = state
            renderer.draw(screen, self.game)
            self.assertNotEqual(screen.get_at((40, 35)), pygame.Color("black"))

    def test_shield_absorbs_then_hull_takes_damage(self):
        self.game.invulnerable = 0
        self.game.hit_player()
        self.assertEqual(self.game.shield, 25)
        self.assertEqual(self.game.lives, 3)
        self.game.invulnerable = 0
        self.game.hit_player()
        self.game.invulnerable = 0
        self.game.hit_player()
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.shield, 0)
        self.game.update(0.05)
        self.assertEqual(self.game.shield, 0)
        self.game.shield_delay = 0
        self.game.update(0.05)
        self.assertGreater(self.game.shield, 0)

    def test_salvage_collection_rank_freeze_and_install(self):
        from progression import Salvage

        self.game.salvage.append(Salvage(self.game.player.position, (0, 0), 12))
        self.game.update(0)
        self.assertEqual(self.game.state, "upgrade")
        self.assertEqual(self.game.rank, 2)
        elapsed = self.game.elapsed
        self.game.update(0.05)
        self.assertEqual(self.game.elapsed, elapsed)
        self.key(pygame.K_1)
        self.assertEqual(self.game.player.weapon_level, 1)
        self.assertEqual(self.game.state, "playing")
        self.game.reset()
        self.assertEqual(self.game.rank, 1)
        self.assertEqual(self.game.player.weapon_level, 0)

    def test_spread_upgrade_and_maxed_modules(self):
        from progression import UPGRADES

        self.game.state = "upgrade"
        self.game.upgrade_choices = ["spread"]
        self.game.apply_upgrade("spread")
        self.game.player.shoot()
        self.assertEqual(len(self.game.shots), 3)
        for key, (_, _, cap) in UPGRADES.items():
            if key != "repair":
                self.game.modules[key] = cap
        self.game.xp = self.game.next_rank
        self.game.check_rank()
        self.assertEqual(self.game.upgrade_choices, ["repair"])
        self.key(pygame.K_3)
        self.assertEqual(self.game.state, "upgrade")
        self.key(pygame.K_1)
        self.assertEqual(self.game.state, "playing")

    def test_flight_boost_energy_and_drag(self):
        from collections import defaultdict

        keys = defaultdict(bool, {pygame.K_w: True, pygame.K_LSHIFT: True})
        with patch("pygame.key.get_pressed", return_value=keys):
            self.game.player.update(0.05)
        self.assertTrue(self.game.player.boosting)
        self.assertLess(self.game.player.energy, 100)
        speed = self.game.player.velocity.length()
        with patch("pygame.key.get_pressed", return_value=defaultdict(bool)):
            self.game.player.update(0.05)
        self.assertLess(self.game.player.velocity.length(), speed)
        self.assertGreater(self.game.player.energy, 98.3)

    def test_contract_combo_and_particle_bounds(self):
        self.game.kills = 14
        Asteroid(200, 200, 20)
        Shot(200, 200)
        self.game.update(0)
        self.assertEqual(self.game.contracts, 1)
        self.assertEqual(self.game.score, 600)
        self.assertEqual(self.game.xp, 8)
        self.game.burst(self.game.player.position, 500)
        self.game.update(0)
        self.assertLessEqual(len(self.game.particles), 300)
        self.game.combo_timer = 0
        self.game.update(0)
        self.assertEqual(self.game.combo, 0)

    def test_motion_mode_does_not_change_spawn_rng(self):
        import random

        snapshots = []
        for reduced in (False, True):
            random.seed(21)
            game = Game(save_scores=False, reduced_motion=reduced)
            game.reset()
            game.player.thrust = 1
            game.burst(game.player.position)
            for _ in range(40):
                game.update(0.05)
            snapshots.append(
                [
                    (tuple(a.position), tuple(a.velocity), a.radius)
                    for a in game.asteroids
                ]
            )
        self.assertEqual(snapshots[0], snapshots[1])


class DisplayTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()

    def test_large_surface_is_cleared_and_game_fills_viewport(self):
        from display import Display

        display = Display()
        display.screen = pygame.display.set_mode((1920, 1080))
        display.screen.fill("magenta")
        display.canvas.fill("navy")
        display.present()
        self.assertEqual(display.screen.get_at((1919, 1079)), pygame.Color("navy"))
        self.assertEqual(display.screen.get_at((0, 0)), pygame.Color("navy"))

    def test_letterbox_clear_resize_and_buffer_reuse(self):
        from display import Display

        display = Display()
        display.screen = pygame.display.set_mode((1000, 800))
        display.canvas.fill("navy")
        display.screen.fill("magenta")
        display.present()
        self.assertEqual(display.screen.get_at((500, 0)), pygame.Color("black"))
        self.assertEqual(display.screen.get_at((500, 400)), pygame.Color("navy"))
        self.assertEqual(display.screen.get_at((500, 799)), pygame.Color("black"))
        buffer = display.scaled
        display.present()
        self.assertIs(display.scaled, buffer)
        display.screen = pygame.display.set_mode((640, 360))
        display.present()
        self.assertEqual(display.scaled.get_size(), (640, 360))

    def test_fullscreen_toggle_keeps_canvas_and_restores_window(self):
        from display import Display

        display = Display()
        canvas = display.canvas
        display.toggle()
        self.assertTrue(display.fullscreen)
        self.assertEqual(
            display.screen.get_size(), pygame.display.get_desktop_sizes()[0]
        )
        display.present()
        # SDL's dummy driver retains desktop dimensions after leaving fullscreen;
        # assert the requested window mode here; exercise native sizes separately.
        with patch("pygame.display.set_mode", wraps=pygame.display.set_mode) as mode:
            display.toggle()
        mode.assert_called_once_with((1280, 720), pygame.RESIZABLE)
        self.assertFalse(display.fullscreen)
        self.assertIs(display.canvas, canvas)

    def test_asteroid_raster_reused_when_only_position_changes(self):
        pygame.display.set_mode((1280, 720))
        rock = Asteroid(100, 100, 40)
        screen = pygame.display.get_surface()
        rock.draw(screen)
        image = rock._image
        rock.position.x += 10
        rock.draw(screen)
        self.assertIs(rock._image, image)
        rock.angle += 0.05
        rock.draw(screen)
        self.assertIsNot(rock._image, image)


if __name__ == "__main__":
    unittest.main()
