# main.py
import pygame
import json
import random
from os.path import join
import sys

# import game modules (these should already exist in the project)
from sprites import Player, Opponent, Ball
from groups import AllSprites
# import POS so we can re-center paddles on resets
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, COLORS, SPEED, POS

def draw_heart(surface, center, size, color):
    """
    Draw a stylized heart (two circles + polygon) at center (x,y).
    """
    x, y = center
    r = max(2, size // 4)
    left_center = (x - r, y - r)
    right_center = (x + r, y - r)
    pygame.draw.circle(surface, color, left_center, r)
    pygame.draw.circle(surface, color, right_center, r)
    bottom_point = (x, y + size // 2)
    points = [
        (x - int(size / 1.5), y - r),
        (x + int(size / 1.5), y - r),
        bottom_point,
    ]
    pygame.draw.polygon(surface, color, points)


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Love Pong")
        self.clock = pygame.time.Clock()
        self.running = True

        # path for persistent score file (keeps previous behavior)
        self.score_path = join('data', 'score.txt')

        # load persistent score if present (but we'll reset for the challenge when it starts)
        try:
            with open(self.score_path, 'r') as f:
                self.score = json.load(f)
        except Exception:
            self.score = {'player': 0, 'opponent': 0}

        # Groups + sprites (constructed same way as original code)
        self.all_sprites = AllSprites()
        self.paddle_sprites = pygame.sprite.Group()

        self.player = Player((self.all_sprites, self.paddle_sprites))
        self.ball = Ball(self.all_sprites, self.paddle_sprites, self.update_score)
        Opponent((self.all_sprites, self.paddle_sprites), self.ball)

        # fonts
        self.title_font = pygame.font.Font(None, 96)
        self.menu_font = pygame.font.Font(None, 48)
        self.score_font = pygame.font.Font(None, 72)
        self.input_font = pygame.font.Font(None, 36)

        # challenge configuration (target score)
        # NOTE: player must reach 26, opponent must reach 7  (player:opponent == 26:7)
        self.TARGET_PLAYER = 26
        self.TARGET_OPPONENT = 7
        self.in_challenge = False
        self.challenge_won = False

        # modal for retry on overshoot
        self.show_retry_modal = False

    def update_score(self, side):
        """
        Called by Ball when a point is scored. `side` is 'player' or 'opponent'.
        We preserve original scoring behavior and additionally check for the challenge target or overshoot.
        """
        if side == 'player':
            self.score['player'] += 1
        else:
            self.score['opponent'] += 1

        # If we're in the special challenge, check target or overshoot (failure)
        if self.in_challenge:
            # exact success: both must match the target simultaneously
            if (self.score['player'] == self.TARGET_PLAYER and
                    self.score['opponent'] == self.TARGET_OPPONENT):
                self.challenge_won = True
            # overshoot: if either side exceeds its target, pause and show the retry modal
            elif (self.score['player'] > self.TARGET_PLAYER) or (self.score['opponent'] > self.TARGET_OPPONENT):
                # Show retry modal and pause in-game updates
                self.show_retry_modal = True

    def reset_challenge_round(self):
        """
        Reset the in-memory score to 0:0 and reposition ball/paddles.
        """
        # Reset scores
        self.score = {'player': 0, 'opponent': 0}
        # Reset ball (Ball.reset() handles serve delay)
        try:
            self.ball.reset()
        except Exception:
            self.ball.rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

        # Reposition paddles to configured starting positions
        try:
            self.player.rect.center = POS['player']
        except Exception:
            self.player.rect.center = (WINDOW_WIDTH - 50, WINDOW_HEIGHT // 2)

        try:
            for s in self.paddle_sprites:
                if getattr(s, 'rect', None) and getattr(s.rect, 'center', None):
                    if s.rect.centerx < WINDOW_WIDTH // 2:
                        s.rect.center = POS['opponent']
                    else:
                        s.rect.center = POS['player']
        except Exception:
            pass

        # hide modal if it was visible
        self.show_retry_modal = False

    def save_score(self):
        """Save score to persistent file (keeps previous behavior)."""
        try:
            with open(self.score_path, 'w') as f:
                json.dump(self.score, f)
        except Exception:
            pass

    def display_score(self):
        """Draw the on-screen score (keeps same arrangement)."""
        player_text = self.score_font.render(str(self.score['player']), True, (255, 255, 255))
        opponent_text = self.score_font.render(str(self.score['opponent']), True, (255, 255, 255))

        center_x = WINDOW_WIDTH // 2
        # opponent (left)
        self.display_surface.blit(opponent_text, (center_x - 150 - opponent_text.get_width() // 2, 30))
        # player (right)
        self.display_surface.blit(player_text, (center_x + 150 - player_text.get_width() // 2, 30))

        # center divider line
        pygame.draw.line(self.display_surface, pygame.Color(COLORS.get('bg detail', '#ffffff')),
                         (center_x, 0), (center_x, WINDOW_HEIGHT), 2)


    def start_menu(self):
        """
        Pink Valentine start menu with hearts and a Play button.
        """
        bg_color = pygame.Color('#ffe6f2')
        heart_color = pygame.Color('#ff4da6')
        play_color = pygame.Color('#e6006f')
        play_hover = pygame.Color('#ff3385')
        text_color = pygame.Color('#ffffff')

        button_w, button_h = 300, 100
        button_x = (WINDOW_WIDTH - button_w) // 2
        button_y = (WINDOW_HEIGHT - button_h) // 2 + 80
        button_rect = pygame.Rect(button_x, button_y, button_w, button_h)

        # hearts positions for decoration
        heart_positions = []
        for i in range(10):
            hx = random.randint(80, WINDOW_WIDTH - 80)
            hy = random.randint(80, WINDOW_HEIGHT - 240)
            sz = random.randint(28, 72)
            heart_positions.append([hx, hy, sz, random.uniform(0.4, 1.0)])

        title_surf = self.title_font.render("Love Pong", True, pygame.Color('#6b003a'))
        subtitle_surf = self.menu_font.render("My Valentine’s twist on Pong for you", True, pygame.Color('#6b003a'))

        in_menu = True
        while in_menu:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_score()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        in_menu = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if button_rect.collidepoint(pygame.mouse.get_pos()):
                        in_menu = False

            # draw background & hearts
            self.display_surface.fill(bg_color)
            for i, h in enumerate(heart_positions):
                hx, hy, sz, phase = h
                bob = int(6 * (0.5 + 0.5 * ((pygame.time.get_ticks() + i * 37) % 1000) / 1000.0 * (1 if i % 2 == 0 else -1)))
                draw_heart(self.display_surface, (hx, hy + bob), sz, heart_color)

            # title
            self.display_surface.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 60))
            self.display_surface.blit(subtitle_surf, ((WINDOW_WIDTH - subtitle_surf.get_width()) // 2, 160))

            # Play button with shadow & hover
            mouse_pos = pygame.mouse.get_pos()
            is_hover = button_rect.collidepoint(mouse_pos)
            current_play_color = play_hover if is_hover else play_color

            shadow_rect = button_rect.copy()
            shadow_rect.y += 6
            pygame.draw.rect(self.display_surface, (200, 0, 80), shadow_rect, border_radius=18)

            pygame.draw.rect(self.display_surface, current_play_color, button_rect, border_radius=18)
            play_text = self.menu_font.render("PLAY", True, text_color)
            self.display_surface.blit(play_text, (button_rect.centerx - play_text.get_width() // 2,
                                                 button_rect.centery - play_text.get_height() // 2))

            instr = self.menu_font.render("Press Enter or click Play", True, pygame.Color('#6b003a'))
            self.display_surface.blit(instr, ((WINDOW_WIDTH - instr.get_width()) // 2, button_rect.bottom + 20))

            pygame.display.update()

    def login_menu(self):
        """
        Username/password login. Hints shown INSIDE the white textboxes.
        Username: "Pavani Gajre"
        Password: "05/02/09"
        """
        screen_bg = pygame.Color('#fff7fb')
        login_color = pygame.Color('#e6006f')
        login_hover = pygame.Color('#ff3385')
        box_color = pygame.Color('#ffffff')
        box_border = pygame.Color('#e0c0d6')
        label_color = pygame.Color('#6b003a')
        text_color = pygame.Color('#000000')
        hint_color = pygame.Color('#b88aa8')

        box_w, box_h = 520, 56
        box_x = (WINDOW_WIDTH - box_w) // 2
        username_y = WINDOW_HEIGHT // 2 - 90
        password_y = username_y + box_h + 24
        username_rect = pygame.Rect(box_x, username_y, box_w, box_h)
        password_rect = pygame.Rect(box_x, password_y, box_w, box_h)

        login_w, login_h = 200, 56
        login_rect = pygame.Rect((WINDOW_WIDTH - login_w) // 2, password_y + box_h + 28, login_w, login_h)

        username_text = ""
        password_text = ""
        active = None
        error_msg = ""
        show_error_for = 0.0

        username_hint = "Your full name"
        password_hint = "Your birthdate(00/00/00)"
        cursor_visible = True
        cursor_timer = 0.0

        correct_username = "Pavani Gajre"
        correct_password = "05/02/09"

        running_login = True
        while running_login:
            dt_ms = self.clock.tick(60)
            dt = dt_ms / 1000.0
            cursor_timer += dt
            if cursor_timer >= 0.5:
                cursor_visible = not cursor_visible
                cursor_timer = 0.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_score()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    if username_rect.collidepoint((mx, my)):
                        active = 'username'
                    elif password_rect.collidepoint((mx, my)):
                        active = 'password'
                    elif login_rect.collidepoint((mx, my)):
                        if username_text.strip() == correct_username and password_text == correct_password:
                            return True
                        else:
                            error_msg = "Incorrect username or password."
                            show_error_for = 2.5
                    else:
                        active = None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        if active == 'username':
                            active = 'password'
                        else:
                            active = 'username'
                    elif event.key == pygame.K_RETURN:
                        if username_text.strip() == correct_username and password_text == correct_password:
                            return True
                        else:
                            error_msg = "Incorrect username or password."
                            show_error_for = 2.5
                    elif event.key == pygame.K_BACKSPACE:
                        if active == 'username':
                            username_text = username_text[:-1]
                        elif active == 'password':
                            password_text = password_text[:-1]
                    else:
                        if active == 'username':
                            if len(username_text) < 36:
                                username_text += event.unicode
                        elif active == 'password':
                            if len(password_text) < 16:
                                password_text += event.unicode

            if show_error_for > 0:
                show_error_for -= dt
                if show_error_for <= 0:
                    error_msg = ""

            # draw
            self.display_surface.fill(screen_bg)

            title = self.title_font.render("Welcome! Please sign in", True, label_color)
            self.display_surface.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 80))

            sub = self.input_font.render("Enter the details to continue to your Pong.", True, label_color)
            self.display_surface.blit(sub, ((WINDOW_WIDTH - sub.get_width()) // 2, 160))

            # boxes
            pygame.draw.rect(self.display_surface, box_color, username_rect, border_radius=8)
            pygame.draw.rect(self.display_surface, box_border, username_rect, width=2, border_radius=8)
            pygame.draw.rect(self.display_surface, box_color, password_rect, border_radius=8)
            pygame.draw.rect(self.display_surface, box_border, password_rect, width=2, border_radius=8)

            # username text or hint
            if username_text == "":
                hint_surf = self.input_font.render(username_hint, True, hint_color)
                self.display_surface.blit(hint_surf, (username_rect.x + 14, username_rect.y + (box_h - hint_surf.get_height()) // 2))
            else:
                name_surf = self.input_font.render(username_text, True, text_color)
                self.display_surface.blit(name_surf, (username_rect.x + 14, username_rect.y + (box_h - name_surf.get_height()) // 2))
                if active == 'username' and cursor_visible:
                    cx = username_rect.x + 14 + name_surf.get_width() + 2
                    cy = username_rect.y + (box_h - name_surf.get_height()) // 2
                    pygame.draw.line(self.display_surface, text_color, (cx, cy), (cx, cy + name_surf.get_height()), 2)

            # password masked or hint
            if password_text == "":
                hint_surf = self.input_font.render(password_hint, True, hint_color)
                self.display_surface.blit(hint_surf, (password_rect.x + 14, password_rect.y + (box_h - hint_surf.get_height()) // 2))
            else:
                masked = "*" * len(password_text)
                pass_surf = self.input_font.render(masked, True, text_color)
                self.display_surface.blit(pass_surf, (password_rect.x + 14, password_rect.y + (box_h - pass_surf.get_height()) // 2))
                if active == 'password' and cursor_visible:
                    cx = password_rect.x + 14 + pass_surf.get_width() + 2
                    cy = password_rect.y + (box_h - pass_surf.get_height()) // 2
                    pygame.draw.line(self.display_surface, text_color, (cx, cy), (cx, cy + pass_surf.get_height()), 2)

            user_label = self.input_font.render("Username", True, label_color)
            pass_label = self.input_font.render("Password", True, label_color)
            self.display_surface.blit(user_label, (username_rect.x, username_rect.y - 34))
            self.display_surface.blit(pass_label, (password_rect.x, password_rect.y - 34))

            # Login button
            mx, my = pygame.mouse.get_pos()
            is_hover = login_rect.collidepoint((mx, my))
            cur_login_color = login_hover if is_hover else login_color
            pygame.draw.rect(self.display_surface, cur_login_color, login_rect, border_radius=10)
            login_text = self.input_font.render("Login", True, pygame.Color('#ffffff'))
            self.display_surface.blit(login_text, (login_rect.centerx - login_text.get_width() // 2,
                                                  login_rect.centery - login_text.get_height() // 2))

            if error_msg:
                err_surf = self.input_font.render(error_msg, True, pygame.Color('#cc0033'))
                self.display_surface.blit(err_surf, ((WINDOW_WIDTH - err_surf.get_width()) // 2, login_rect.bottom + 18))

            help_surf = self.input_font.render("Hint: Username is 'Pavani Gajre' and the password is your birthdate.", True, pygame.Color('#8a5a73'))
            self.display_surface.blit(help_surf, ((WINDOW_WIDTH - help_surf.get_width()) // 2, login_rect.bottom + 60))

            pygame.display.update()

        return False

    def challenge_menu(self):
        """
        Third popup with the exact text requested and a Continue button.
        After Continue the challenge begins (score reset to 0:0 and in_challenge flag enabled).
        """
        # preserve user's wording (keeps typos as provided)
        message_lines = [
            "I love you so much Pavani. But to see that love I have a challengge for you.",
            "Try to get the pong score equal the day we made it official."
        ]

        # UI colors
        bg = pygame.Color('#fff0f7')
        heart_col = pygame.Color('#ff4da6')
        box_col = pygame.Color('#ffd6eb')
        text_col = pygame.Color('#6b003a')
        cont_col = pygame.Color('#e6006f')
        cont_hover = pygame.Color('#ff3385')
        cont_w, cont_h = 280, 70
        cont_rect = pygame.Rect((WINDOW_WIDTH - cont_w)//2, WINDOW_HEIGHT - 180, cont_w, cont_h)

        # decorative hearts
        hearts = []
        for i in range(12):
            hearts.append((random.randint(60, WINDOW_WIDTH-60), random.randint(120, WINDOW_HEIGHT-220), random.randint(22, 56)))

        in_popup = True
        while in_popup:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_score()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if cont_rect.collidepoint(pygame.mouse.get_pos()):
                        in_popup = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        in_popup = False

            # draw
            self.display_surface.fill(bg)

            # floating hearts
            for i, (hx, hy, sz) in enumerate(hearts):
                bob = int(4 * (1 + ((pygame.time.get_ticks() + i * 43) % 1000) / 1000.0))
                draw_heart(self.display_surface, (hx, hy + bob), sz, heart_col)

            # message box
            box_w = WINDOW_WIDTH - 140
            box_h = 240
            box_x = 70
            box_y = 140
            pygame.draw.rect(self.display_surface, box_col, (box_x, box_y, box_w, box_h), border_radius=14)
            pygame.draw.rect(self.display_surface, pygame.Color('#e0a6c7'), (box_x, box_y, box_w, box_h), width=3, border_radius=14)

            # render message lines centered
            y_offset = box_y + 28
            for line in message_lines:
                m = self.input_font.render(line, True, text_col)
                self.display_surface.blit(m, ((WINDOW_WIDTH - m.get_width()) // 2, y_offset))
                y_offset += m.get_height() + 14

            # Continue button
            mx, my = pygame.mouse.get_pos()
            is_hover = cont_rect.collidepoint((mx, my))
            cur_col = cont_hover if is_hover else cont_col
            pygame.draw.rect(self.display_surface, cur_col, cont_rect, border_radius=14)
            cont_text = self.menu_font.render("Continue", True, pygame.Color('#ffffff'))
            self.display_surface.blit(cont_text, (cont_rect.centerx - cont_text.get_width() // 2,
                                                  cont_rect.centery - cont_text.get_height() // 2))

            pygame.display.update()

        # When continuing, reset the in-memory score for the challenge and enable challenge mode
        self.score = {'player': 0, 'opponent': 0}
        self.in_challenge = True
        self.challenge_won = False
        # ensure ball/paddles are centered at start
        try:
            self.ball.reset()
        except Exception:
            pass
        try:
            self.player.rect.center = POS['player']
        except Exception:
            pass
        for s in self.paddle_sprites:
            if s.rect.centerx < WINDOW_WIDTH // 2:
                try:
                    s.rect.center = POS['opponent']
                except Exception:
                    pass
            else:
                try:
                    s.rect.center = POS['player']
                except Exception:
                    pass


    def draw_retry_modal(self):
        """
        Draws the centered modal asking "Would you like to retry?" with Yes/No buttons.
        Returns rects for yes/no so caller can use them for hit testing.
        """
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.display_surface.blit(overlay, (0, 0))

        # modal box
        box_w = 740
        box_h = 240
        box_x = (WINDOW_WIDTH - box_w) // 2
        box_y = (WINDOW_HEIGHT - box_h) // 2 - 20
        pygame.draw.rect(self.display_surface, pygame.Color('#fff0f7'), (box_x, box_y, box_w, box_h), border_radius=14)
        pygame.draw.rect(self.display_surface, pygame.Color('#e0a6c7'), (box_x, box_y, box_w, box_h), width=3, border_radius=14)

        # text
        title = self.menu_font.render("Would you like to retry?", True, pygame.Color('#6b003a'))
        sub = self.input_font.render(f"A side exceeded the target before reaching {self.TARGET_OPPONENT}:{self.TARGET_PLAYER}. Retry will reset score to 0:0.", True, pygame.Color('#6b003a'))
        self.display_surface.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, box_y + 28))
        self.display_surface.blit(sub, ((WINDOW_WIDTH - sub.get_width()) // 2, box_y + 28 + title.get_height() + 14))

        # Yes / No buttons
        btn_w, btn_h = 180, 64
        spacing = 40
        total_w = btn_w * 2 + spacing
        start_x = (WINDOW_WIDTH - total_w) // 2
        btn_y = box_y + box_h - btn_h - 20

        yes_rect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        no_rect = pygame.Rect(start_x + btn_w + spacing, btn_y, btn_w, btn_h)

        # draw buttons (hover logic handled by caller via mouse pos)
        mx, my = pygame.mouse.get_pos()
        yes_hover = yes_rect.collidepoint((mx, my))
        no_hover = no_rect.collidepoint((mx, my))

        yes_color = pygame.Color('#e6006f') if not yes_hover else pygame.Color('#ff3385')
        no_color = pygame.Color('#9a2b4a') if not no_hover else pygame.Color('#b04366')

        pygame.draw.rect(self.display_surface, yes_color, yes_rect, border_radius=12)
        pygame.draw.rect(self.display_surface, no_color, no_rect, border_radius=12)

        yes_text = self.menu_font.render("Yes", True, pygame.Color('#ffffff'))
        no_text = self.menu_font.render("No", True, pygame.Color('#ffffff'))

        self.display_surface.blit(yes_text, (yes_rect.centerx - yes_text.get_width() // 2, yes_rect.centery - yes_text.get_height() // 2))
        self.display_surface.blit(no_text, (no_rect.centerx - no_text.get_width() // 2, no_rect.centery - no_text.get_height() // 2))

        return yes_rect, no_rect


    def final_menu(self):
        """
        Final romantic popup when the target score is reached.
        Shows the message "May I be your Valentine?" and a big button to finish.
        """
        bg = pygame.Color('#fff0f7')
        heart_col = pygame.Color('#ff4da6')
        box_col = pygame.Color('#ffd6eb')
        text_col = pygame.Color('#6b003a')
        btn_col = pygame.Color('#e6006f')
        btn_hover = pygame.Color('#ff3385')

        btn_w, btn_h = 360, 88
        btn_rect = pygame.Rect((WINDOW_WIDTH - btn_w)//2, WINDOW_HEIGHT - 200, btn_w, btn_h)

        in_final = True
        while in_final:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_score()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_rect.collidepoint(pygame.mouse.get_pos()):
                        in_final = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        in_final = False

            # draw
            self.display_surface.fill(bg)

            # some decorative hearts
            for i in range(10):
                hx = 80 + (i * 120) % (WINDOW_WIDTH - 160)
                hy = 120 + ((i * 73) % 260)
                sz = 28 + (i % 4) * 8
                bob = int(5 * ((pygame.time.get_ticks() + i * 31) % 1000) / 1000.0)
                draw_heart(self.display_surface, (hx, hy + bob), sz, heart_col)

            # message box
            box_w = WINDOW_WIDTH - 220
            box_h = 180
            box_x = 110
            box_y = 140
            pygame.draw.rect(self.display_surface, box_col, (box_x, box_y, box_w, box_h), border_radius=12)
            pygame.draw.rect(self.display_surface, pygame.Color('#e0a6c7'), (box_x, box_y, box_w, box_h), width=2, border_radius=12)

            # big question
            q = self.menu_font.render("May I be your Valentine?", True, text_col)
            self.display_surface.blit(q, ((WINDOW_WIDTH - q.get_width()) // 2, box_y + (box_h - q.get_height()) // 2 - 6))

            # button
            mx, my = pygame.mouse.get_pos()
            is_hover = btn_rect.collidepoint((mx, my))
            cur_col = btn_hover if is_hover else btn_col
            pygame.draw.rect(self.display_surface, cur_col, btn_rect, border_radius=18)
            btn_text = self.menu_font.render("Be Mine", True, pygame.Color('#ffffff'))
            self.display_surface.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2,
                                                btn_rect.centery - btn_text.get_height() // 2))

            pygame.display.update()

        # after final popup, save score and exit gracefully
        self.save_score()
        pygame.quit()
        sys.exit()

    def run(self):
        # 1) start menu
        self.start_menu()

        # 2) login screen
        login_ok = self.login_menu()
        if not login_ok:
            self.save_score()
            pygame.quit()
            return

        # 3) challenge popup
        self.challenge_menu()

        # 4) gameplay loop — run until the player reaches the target (self.challenge_won set in update_score)
        # We do not change any gameplay parameters or difficulty.
        while True:
            dt = self.clock.tick(60) / 1000.0

            # process events first (this also handles modal interactions)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_score()
                    pygame.quit()
                    sys.exit()
                # when retry modal is visible, let clicks on Yes/No be handled below in drawing section
                if event.type == pygame.KEYDOWN:
                    # allow Esc to behave like "No" (return to start menu)
                    if event.key == pygame.K_ESCAPE and self.show_retry_modal:
                        # treat as "No"
                        self.show_retry_modal = False
                        self.in_challenge = False
                        # Return to start menu flow
                        self.start_menu()
                        login_ok = self.login_menu()
                        if not login_ok:
                            self.save_score()
                            pygame.quit()
                            return
                        self.challenge_menu()

            # PINK gameplay background + subtle floating hearts (visual only)
            game_bg = pygame.Color('#ffe6f2')
            heart_col = pygame.Color('#ff4da6')
            self.display_surface.fill(game_bg)

            # faint decorative hearts behind action
            t = pygame.time.get_ticks()
            for i in range(6):
                hx = 60 + (i * 180) % (WINDOW_WIDTH - 120)
                hy = 140 + ((i * 97 + (t//200) * (i+1)) % 240)
                sz = 18 + (i % 3) * 6
                heart_surface = pygame.Surface((sz*2+6, sz*2+6), pygame.SRCALPHA)
                draw_heart(heart_surface, (sz+3, sz+3), sz, pygame.Color(255, 77, 166, 22))
                self.display_surface.blit(heart_surface, (hx - heart_surface.get_width()//2, hy - heart_surface.get_height()//2))

            # If retry modal is shown, pause gameplay updates (freeze the action)
            if not self.show_retry_modal:
                self.all_sprites.update(dt)

            # draw sprites regardless (so they appear static if paused)
            self.all_sprites.draw()

            # draw current score overlay
            self.display_score()

            # draw retry modal if triggered
            if self.show_retry_modal:
                yes_rect, no_rect = self.draw_retry_modal()
                for e in pygame.event.get([pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]):
                    # only care about mousebuttondown 1
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        if yes_rect.collidepoint((mx, my)):
                            # user chose to retry: reset round and continue
                            self.reset_challenge_round()
                        elif no_rect.collidepoint((mx, my)):
                            # user chose No: exit challenge and go back to start menu flow
                            self.show_retry_modal = False
                            self.in_challenge = False
                            # go back to start menu; require login again if they play
                            self.start_menu()
                            login_ok = self.login_menu()
                            if not login_ok:
                                self.save_score()
                                pygame.quit()
                                return
                            # If they choose to continue after returning to menus, re-run the challenge popup
                            self.challenge_menu()
                            # After returning from challenge_menu, continue loop normally
            # If the challenge has been won, show final menu and then exit.
            if self.in_challenge and self.challenge_won:
                self.final_menu()
                break

            pygame.display.update()


if __name__ == "__main__":

    Game().run()
