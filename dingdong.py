import pygame
import sys
import cv2
import mediapipe as mp
import numpy as np
import json
import os

pygame.init()
pygame.mixer.init()  # Initialize sound mixer

# Constants
WIDTH, HEIGHT = 1280, 720
FPS = 60
BG_COLOR = (20, 30, 40)
BAT1_COLOR = (50, 100, 255)   # Blue left paddle
BAT2_COLOR = (255, 50, 50)    # Red right paddle
BALL_COLOR = (255, 255, 255)
FONT_COLOR = (255, 255, 255)

# Create screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Single Player Pong - Both Hands Control")

clock = pygame.time.Clock()

BAT_WIDTH, BAT_HEIGHT = 20, 120
bat1_x, bat1_y = 50, HEIGHT // 2 - BAT_HEIGHT // 2
bat2_x, bat2_y = WIDTH - 50 - BAT_WIDTH, HEIGHT // 2 - BAT_HEIGHT // 2

ball_radius = 20
ball_x, ball_y = WIDTH // 2, HEIGHT // 2

ball_speed_x, ball_speed_y = 25, 25
speed_increment = 1.2
max_speed = 40

score = 0
player_name = "Player"
game_over = False
paused = False
recording = False
video_writer = None

# Sound effects
try:
    paddle_sound = pygame.mixer.Sound("paddle.wav")
    wall_sound = pygame.mixer.Sound("wall.wav")
    score_sound = pygame.mixer.Sound("score.wav")
    game_over_sound = pygame.mixer.Sound("game_over.wav")
except:
    # Dummy silent sounds if files missing
    paddle_sound = pygame.mixer.Sound(buffer=bytearray([0] * 44))
    wall_sound = pygame.mixer.Sound(buffer=bytearray([0] * 44))
    score_sound = pygame.mixer.Sound(buffer=bytearray([0] * 44))
    game_over_sound = pygame.mixer.Sound(buffer=bytearray([0] * 44))
    print("Sound files not found. Using silent sounds.")

# Fonts
font = pygame.font.SysFont(None, 72)
small_font = pygame.font.SysFont(None, 36)
name_font = pygame.font.SysFont(None, 48)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

# Top score system
TOP_SCORE_FILE = "top_score.json"
top_score = {"name": "No one", "score": 0}

def load_top_score():
    global top_score
    try:
        if os.path.exists(TOP_SCORE_FILE):
            with open(TOP_SCORE_FILE, 'r') as f:
                top_score = json.load(f)
    except:
        print("Could not load top score")

def save_top_score():
    try:
        with open(TOP_SCORE_FILE, 'w') as f:
            json.dump(top_score, f)
    except:
        print("Could not save top score")

def reflect_ball(paddle_y, ball_y):
    # Calculate reflection angle based on hit position on paddle
    relative_intersect = (paddle_y + BAT_HEIGHT/2) - ball_y
    normalized_intersect = relative_intersect / (BAT_HEIGHT/2)
    max_bounce_angle = np.pi / 3  # 60 degrees max bounce angle
    bounce_angle = normalized_intersect * max_bounce_angle
    return bounce_angle

def draw():
    screen.fill(BG_COLOR)
    pygame.draw.rect(screen, BAT1_COLOR, (bat1_x, bat1_y, BAT_WIDTH, BAT_HEIGHT))
    pygame.draw.rect(screen, BAT2_COLOR, (bat2_x, bat2_y, BAT_WIDTH, BAT_HEIGHT))
    pygame.draw.circle(screen, BALL_COLOR, (int(ball_x), int(ball_y)), ball_radius)
    
    # Score display
    score_text = font.render(f"Score: {score}", True, FONT_COLOR)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 30))
    
    # Top score display
    top_score_text = small_font.render(f"Top: {top_score['name']} - {top_score['score']}", True, FONT_COLOR)
    screen.blit(top_score_text, (20, 20))
    
    # Player name display
    name_text = name_font.render(player_name, True, (200, 200, 255))
    screen.blit(name_text, (WIDTH - name_text.get_width() - 20, 20))
    
    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        
        box_w, box_h = 600, 300
        box_x, box_y = WIDTH//2 - box_w//2, HEIGHT//2 - box_h//2
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box_surf.fill((30, 30, 30, 200))
        screen.blit(box_surf, (box_x, box_y))
        pygame.draw.rect(screen, (200, 200, 200), (box_x, box_y, box_w, box_h), 4, border_radius=20)
        
        go_text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(go_text, (WIDTH//2 - go_text.get_width()//2, box_y + 50))
        
        if score > top_score["score"]:
            new_top = font.render("NEW TOP SCORE!", True, (50, 255, 50))
            screen.blit(new_top, (WIDTH//2 - new_top.get_width()//2, box_y + 130))
        
        restart_text = small_font.render("Press R to Restart or Q to Quit", True, FONT_COLOR)
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, box_y + 230))
        
    if paused:
        pause_text = font.render("PAUSED", True, (255, 255, 0))
        screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2))

def ball_reset():
    global ball_x, ball_y, ball_speed_x, ball_speed_y, game_over
    ball_x, ball_y = WIDTH // 2, HEIGHT // 2
    ball_speed_x = 35 * np.random.choice([-1, 1])
    ball_speed_y = 35 * np.random.choice([-1, 1])
    game_over = False

def hand_to_paddle_y(hand_landmarks):
    wrist_y = hand_landmarks.landmark[0].y
    paddle_y = int(wrist_y * HEIGHT) - BAT_HEIGHT // 2
    return max(0, min(HEIGHT - BAT_HEIGHT, paddle_y))

load_top_score()

name_input = ""
name_active = True
print("Enter your name and press Enter: ", end="")

ball_reset()

running = True
while running:
    clock.tick(FPS)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if name_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    player_name = name_input if name_input else "Player"
                    name_active = False
                    print(player_name)
                elif event.key == pygame.K_BACKSPACE:
                    name_input = name_input[:-1]
                elif event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    if event.unicode.isprintable():
                        name_input += event.unicode
                        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and game_over:
                score = 0
                ball_reset()
            if event.key == pygame.K_q:
                running = False
            if event.key == pygame.K_p:
                paused = not paused
            if event.key == pygame.K_s:
                pygame.image.save(screen, "screenshot.png")
                print("Screenshot saved as screenshot.png")
            if event.key == pygame.K_v:
                recording = not recording
                if recording:
                    video_writer = cv2.VideoWriter('gameplay.avi', cv2.VideoWriter_fourcc(*'XVID'), FPS, (WIDTH, HEIGHT))
                    print("Recording started")
                else:
                    if video_writer:
                        video_writer.release()
                    print("Recording stopped")

    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if not game_over and not name_active and not paused:
        left_paddle_y = bat1_y
        right_paddle_y = bat2_y

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                y_pos = hand_to_paddle_y(hand_landmarks)
                if label == 'Left':
                    left_paddle_y = y_pos
                elif label == 'Right':
                    right_paddle_y = y_pos

        bat1_y = left_paddle_y
        bat2_y = right_paddle_y

        ball_x += ball_speed_x
        ball_y += ball_speed_y

        if ball_y - ball_radius <= 0 or ball_y + ball_radius >= HEIGHT:
            wall_sound.play()
            ball_speed_y *= -1

        bat1_rect = pygame.Rect(bat1_x, bat1_y, BAT_WIDTH, BAT_HEIGHT)
        bat2_rect = pygame.Rect(bat2_x, bat2_y, BAT_WIDTH, BAT_HEIGHT)
        ball_rect = pygame.Rect(ball_x - ball_radius, ball_y - ball_radius, ball_radius * 2, ball_radius * 2)

        hit = False
        if ball_rect.colliderect(bat1_rect):
            paddle_sound.play()
            bounce_angle = reflect_ball(bat1_y, ball_y)
            speed = min(abs(ball_speed_x) * speed_increment, max_speed)
            ball_speed_x = speed
            ball_speed_y = -speed * np.tan(bounce_angle)
            ball_x = bat1_x + BAT_WIDTH + ball_radius
            hit = True
        elif ball_rect.colliderect(bat2_rect):
            paddle_sound.play()
            bounce_angle = reflect_ball(bat2_y, ball_y)
            speed = max(abs(ball_speed_x) * speed_increment, max_speed)
            ball_speed_x = -speed
            ball_speed_y = -speed * np.tan(bounce_angle)
            ball_x = bat2_x - ball_radius
            hit = True

        if hit:
            score_sound.play()
            score += 1

        if ball_x < 0 or ball_x > WIDTH:
            game_over_sound.play()
            game_over = True
            if score > top_score["score"]:
                top_score = {"name": player_name, "score": score}
                save_top_score()

    draw()

    if name_active:
        input_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 25, 400, 50)
        pygame.draw.rect(screen, (50, 50, 70), input_rect)
        pygame.draw.rect(screen, (100, 100, 200), input_rect, 2)
        prompt_text = small_font.render("Enter your name:", True, FONT_COLOR)
        screen.blit(prompt_text, (WIDTH//2 - prompt_text.get_width()//2, HEIGHT//2 - 70))
        name_surface = small_font.render(name_input, True, (255, 255, 200))
        screen.blit(name_surface, (input_rect.x + 10, input_rect.y + 10))
        cursor_pos = name_surface.get_width() + 15
        if pygame.time.get_ticks() % 1000 < 500:
            pygame.draw.line(screen, (200, 200, 255), (input_rect.x + cursor_pos, input_rect.y + 10),
                             (input_rect.x + cursor_pos, input_rect.y + 40), 2)

    # Show webcam feed
    w, h = 320, 240
    frame_small = cv2.resize(frame, (w, h))
    frame_small = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
    frame_small = cv2.rotate(frame_small, cv2.ROTATE_90_CLOCKWISE)
    frame_small = cv2.flip(frame_small, 1)
    frame_surface = pygame.surfarray.make_surface(frame_small)
    screen.blit(frame_surface, ((WIDTH - w) // 2, HEIGHT - h - 10))

    pygame.display.flip()

    # Save video frame if recording
    if recording:
        video_frame = pygame.surfarray.array3d(screen)
        video_frame = np.rot90(video_frame, 3)
        video_frame = cv2.cvtColor(video_frame, cv2.COLOR_RGB2BGR)
        video_writer.write(video_frame)

cap.release()
if recording and video_writer:
    video_writer.release()
pygame.quit()
sys.exit()
