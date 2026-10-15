import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from asteroid import Asteroid
from shot import Shot
from game import Game, score_path
from ui import Renderer
from constants import SCREEN_WIDTH


class GameTests(unittest.TestCase):
    def test_empty_state_home_uses_home_directory(self):
        home = Path(tempfile.gettempdir()) / "asteroids-test-home"
        with patch.dict(os.environ, {"XDG_STATE_HOME": ""}), patch.object(Path, "home", return_value=home):
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

    def test_lives_protection_and_best_score(self):
        self.game.score = 120
        self.game.hit_player()
        self.assertEqual(self.game.lives, 3)
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

    def test_corrupt_score_and_write_failure(self):
        self.game.save_path.write_text("[]")
        self.assertEqual(Game(self.game.save_path).best, 0)
        self.game.score = 10
        with patch("game.tempfile.NamedTemporaryFile", side_effect=OSError("read-only")):
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
        self.assertEqual(list(self.game.save_path.parent.iterdir()), [self.game.save_path])

    def test_render_all_states(self):
        renderer = Renderer()
        screen = pygame.display.get_surface()
        for state in ["title", "playing", "paused", "game_over"]:
            self.game.state = state
            renderer.draw(screen, self.game)
            self.assertNotEqual(screen.get_at((40, 35)), pygame.Color("black"))


if __name__ == "__main__":
    unittest.main()
