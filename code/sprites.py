from settings import *
from random import choice, uniform
from pathlib import Path
import pygame

# Optional Pillow import (used only if pygame fails to load some PNGs)
try:
    from PIL import Image
except Exception:
    Image = None


class Paddle(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)

        # --- Try to load lp_image.png from project/data, rotate 90° right (clockwise),
        # and fit it into SIZE['paddle'] while preserving aspect ratio. ---
        assets_dir = Path(__file__).resolve().parent.parent / 'data'
        png_path = assets_dir / 'lp_image.png'

        target_size = tuple(SIZE['paddle'])  # final surface size we want for paddle (w, h)
        final_surf = None

        # Helper to take a pygame Surface, optionally rotate, scale preserving aspect to fit target_size,
        # and return a new Surface of size target_size with the scaled image centered.
        def prepare_surface_from_pygame_surf(surf: pygame.Surface, rotate_clockwise: bool = True):
            # rotate (pygame.rotate uses counter-clockwise, so negative angle for clockwise)
            rotated = pygame.transform.rotate(surf, -90) if rotate_clockwise else surf.copy()
            rw, rh = rotated.get_size()
            tw, th = target_size

            # compute scale factor preserving aspect ratio
            scale = min(tw / rw, th / rh)
            new_w = max(1, int(round(rw * scale)))
            new_h = max(1, int(round(rh * scale)))

            scaled = pygame.transform.smoothscale(rotated, (new_w, new_h))

            # create final surface with transparency and blit scaled centered
            surf_final = pygame.Surface((tw, th), pygame.SRCALPHA)
            x = (tw - new_w) // 2
            y = (th - new_h) // 2
            surf_final.blit(scaled, (x, y))
            return surf_final

        # 1) Try pygame.image.load first (fast and typical for PNG)
        if png_path.exists():
            try:
                loaded = pygame.image.load(str(png_path))
                try:
                    loaded = loaded.convert_alpha()
                except Exception:
                    loaded = loaded.convert()
                final_surf = prepare_surface_from_pygame_surf(loaded, rotate_clockwise=True)
            except Exception:
                final_surf = None

        # 2) If pygame failed and Pillow is available, try Pillow route
        if final_surf is None and Image is not None and png_path.exists():
            try:
                pil_img = Image.open(str(png_path)).convert("RGBA")
                pil_rot = pil_img.rotate(-90, expand=True)  # rotate clockwise
                raw = pil_rot.tobytes()
                size = pil_rot.size  # (w, h)
                surf = pygame.image.fromstring(raw, size, 'RGBA')
                final_surf = prepare_surface_from_pygame_surf(surf, rotate_clockwise=False)
            except Exception:
                final_surf = None

        # 3) Final fallback: draw the original rounded rectangle paddle (exact target_size)
        if final_surf is None:
            final_surf = pygame.Surface(target_size, pygame.SRCALPHA)
            pygame.draw.rect(
                final_surf,
                COLORS['paddle'],
                pygame.Rect((0, 0), target_size),
                0,
                4
            )

        # Use final_surf as the visible paddle image
        self.image = final_surf

        # --- Create a tinted shadow surface that preserves alpha ---
        try:
            self.shadow_surf = self.image.copy()
            tint = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            tint.fill(pygame.Color(COLORS['paddle shadow']))
            self.shadow_surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            self.shadow_surf = self.image.copy()

        # rect & movement (center at player pos by default)
        self.rect = self.image.get_rect(center=POS['player'])
        self.old_rect = self.rect.copy()
        self.direction = 0

    def move(self, dt):
        self.rect.centery += self.direction * self.speed * dt
        self.rect.top = 0 if self.rect.top < 0 else self.rect.top
        self.rect.bottom = WINDOW_HEIGHT if self.rect.bottom > WINDOW_HEIGHT else self.rect.bottom   

    def update(self, dt):
        self.old_rect = self.rect.copy()
        self.get_direction()
        self.move(dt)


class Player(Paddle):
    def __init__(self, groups):
        super().__init__(groups)
        self.speed = SPEED['player']

    def get_direction(self):
        keys = pygame.key.get_pressed()
        self.direction = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])


class Opponent(Paddle):
    def __init__(self, groups, ball):
        super().__init__(groups)
        self.speed = SPEED['opponent']
        self.rect.center = POS['opponent']
        self.ball = ball

    def get_direction(self):
        # simple chase AI: move towards ball's center
        self.direction = 1 if self.ball.rect.centery > self.rect.centery else -1


class Ball(pygame.sprite.Sprite):
    def __init__(self, groups, paddle_sprites, update_score):
        super().__init__(groups)
        self.paddle_sprites = paddle_sprites
        self.update_score = update_score

        # Target logical size (keep this exact)
        target_size = tuple(SIZE['ball'])  # (w, h)
        assets_dir = Path(__file__).resolve().parent.parent / 'data'

        # Known filename (adjust if your filesystem encoded characters differently)
        filename_candidates = [
            'Pngtree—mango cartoon_6016091.png',  # exact name with em dash
            'Pngtree-mango cartoon_6016091.png',  # hyphen fallback
            'Pngtree_mango cartoon_6016091.png',  # underscore fallback
            'mango cartoon_6016091.png'           # simpler fallback
        ]

        png_path = None
        for fn in filename_candidates:
            p = assets_dir / fn
            if p.exists():
                png_path = p
                break

        # Helper: fit a pygame surface into target_size preserving aspect ratio and center it
        def fit_into_target(surf: pygame.Surface, target):
            tw, th = target
            rw, rh = surf.get_size()
            scale = min(tw / rw, th / rh)
            new_w = max(1, int(round(rw * scale)))
            new_h = max(1, int(round(rh * scale)))
            scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
            surf_final = pygame.Surface((tw, th), pygame.SRCALPHA)
            x = (tw - new_w) // 2
            y = (th - new_h) // 2
            surf_final.blit(scaled, (x, y))
            return surf_final

        final_ball_surf = None

        # 1) Try pygame to load image
        if png_path is not None:
            try:
                loaded = pygame.image.load(str(png_path))
                try:
                    loaded = loaded.convert_alpha()
                except Exception:
                    loaded = loaded.convert()
                final_ball_surf = fit_into_target(loaded, target_size)
            except Exception:
                final_ball_surf = None

        # 2) If pygame failed and Pillow is available, try Pillow route
        if final_ball_surf is None and Image is not None and png_path is not None:
            try:
                pil_img = Image.open(str(png_path)).convert("RGBA")
                # no rotation; just use the original orientation
                raw = pil_img.tobytes()
                size = pil_img.size
                surf = pygame.image.fromstring(raw, size, 'RGBA')
                final_ball_surf = fit_into_target(surf, target_size)
            except Exception:
                final_ball_surf = None

        # 3) Fallback: draw original circular ball on target_size surface
        if final_ball_surf is None:
            final_ball_surf = pygame.Surface(target_size, pygame.SRCALPHA)
            radius = int(target_size[0] / 2)
            center = (target_size[0] / 2, target_size[1] / 2)
            pygame.draw.circle(final_ball_surf, COLORS['ball'], center, radius)

        # set image and shadow
        self.image = final_ball_surf
        try:
            self.shadow_surf = self.image.copy()
            tint = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            tint.fill(pygame.Color(COLORS['ball shadow']))
            self.shadow_surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            self.shadow_surf = self.image.copy()

        # rect & movement (center on screen)
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.old_rect = self.rect.copy()
        self.direction = pygame.Vector2(choice((1, -1)), uniform(0.7, 0.8) * choice((-1, 1)))
        self.speed_modifier = 0

        # timer
        self.start_time = pygame.time.get_ticks()
        self.duration = 1200

    def move(self, dt):
        self.rect.x += self.direction.x * SPEED['ball'] * dt * self.speed_modifier
        self.collision('horizontal')
        self.rect.y += self.direction.y * SPEED['ball'] * dt * self.speed_modifier
        self.collision('vertical')

    def collision(self, direction):
        for sprite in self.paddle_sprites:
            if sprite.rect.colliderect(self.rect):
                if direction == 'horizontal':
                    if self.rect.right >= sprite.rect.left and self.old_rect.right <= sprite.old_rect.left:
                        self.rect.right = sprite.rect.left
                        self.direction.x *= -1
                    if self.rect.left <= sprite.rect.right and self.old_rect.left >= sprite.old_rect.right:
                        self.rect.left = sprite.rect.right
                        self.direction.x *= -1
                else:
                    if self.rect.bottom >= sprite.rect.top and self.old_rect.bottom <= sprite.old_rect.top:
                        self.rect.bottom = sprite.rect.top
                        self.direction.y *= -1
                    if self.rect.top <= sprite.rect.bottom and self.old_rect.top >= sprite.old_rect.bottom:
                        self.rect.top = sprite.rect.bottom
                        self.direction.y *= -1

    def wall_collision(self):
        if self.rect.top <= 0:
            self.rect.top = 0
            self.direction.y *= -1

        if self.rect.bottom >= WINDOW_HEIGHT:
            self.rect.bottom = WINDOW_HEIGHT
            self.direction.y *= -1

        if self.rect.right >= WINDOW_WIDTH or self.rect.left <= 0:
            self.update_score('player' if self.rect.x < WINDOW_WIDTH / 2 else 'opponent')
            self.reset()

    def reset(self):
        self.rect.center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        self.direction = pygame.Vector2(choice((1, -1)), uniform(0.7, 0.8) * choice((-1, 1)))
        self.start_time = pygame.time.get_ticks()

    def timer(self):
        if pygame.time.get_ticks() - self.start_time >= self.duration:
            self.speed_modifier = 1
        else:
            self.speed_modifier = 0

    def update(self, dt):
        self.old_rect = self.rect.copy()
        self.timer()
        self.move(dt)
        self.wall_collision()
