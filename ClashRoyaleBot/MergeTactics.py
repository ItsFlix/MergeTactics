import time
import pyautogui
import threading
import os
import random
import keyboard
import cv2
import numpy as np
import mss

pyautogui.useImageNotFoundException()

# === Folder Directories ===
main_dir = "C:/Users/???/Desktop/ClashRoyaleBot/MergeTactics"
elixir_folder_dir = maindir + "/Elixir"
cards_folder_dir = maindir + "/Cards"
properties_folder_dir = maindir + "/Properties"


# === Shared Global Elixir State ===
Elixir = 0
elixir_lock = threading.Lock()

# === Elixir Bar and Hand Card Regions ===
REGION = {
    "top": 816,
    "left": 702,
    "width": 547,
    "height": 193
}

CARD_REGION = (756, 829, 448, 177)


# Memory: permanent list of played cards
bot_memory = {
    "elixir": 0,
    "played_cards": [],     # Cards that were played this cycle
    "field_slots": {},      # Like {"slot1": "Archer", "slot2": "Bomber"}
}

# === Card Elixir Costs (Fixed: missing .png on RoyalGhost) ===
card_costs = {
    "Archer.png": 2,
    "Barbarian.png": 2,
    "Bomber.png": 2,
    "Executioner.png": 3,
    "GiantSkeleton.png": 3,
    "Goblin.png": 2,
    "GoblinMachine.png": 4,
    "GoldenKnight.png": 5,
    "Pekka.png": 3,
    "Princess.png": 4,
    "Valkyrie.png": 3,
    "Knight.png": 2,
    "SpearGoblin.png": 2,
    "Bandit.png": 4,
    "DartGoblin.png": 3,
    "Prince.png": 3,
    "MegaKnight.png": 4,
    "RoyalGhost.png": 4,
    "SkeletonKing.png": 5,
    "ArcherQueen.png": 5,
}

# === Priority Cards (Whitelist First Strategy) ===
priority_cards = [
    "MegaKnight.png",
    "GoldenKnight.png",
    "SkeletonKing.png",
    "Pekka.png",
    "Executioner.png",
    "Princess.png"
]


card_combos = [
    ("Barbarian.png", "Archer.png", "Valkyrie.png", "ArcherQueen.png"),
    ("Princess.png", "Executioner.png", "MegaKnight.png"),
]

# === Detect Elixir from Image ===
def elixir_detector_loop():
    global Elixir
    elixir_images = [(f"{i}.png", i) for i in range(11)]

    while True:
        if keyboard.is_pressed('q'):
            print("Elixir detector stopped by user.")
            break

        with mss.mss() as sct:
            screenshot = sct.grab((REGION["left"], REGION["top"], REGION["left"] + REGION["width"], REGION["top"] + REGION["height"]))
            screen_img = np.array(screenshot)
            gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

            for img_name, elixir_value in elixir_images:
                try:
                    template = cv2.imread(os.path.join(elixir_folder_dir, img_name), cv2.IMREAD_GRAYSCALE)
                    if template is None:
                        continue

                    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)

                    if max_val > 0.9:
                        with elixir_lock:
                            Elixir = elixir_value
                        print(f"Elixir = {elixir_value}")
                        break  # Stop after first match
                except Exception as e:
                    print(f"[ERROR] Elixir detection failed for {img_name}: {e}")

        time.sleep(0.1)

# === Check Cards That Can Be Played Based on Elixir ===
def CheckPlayableCards():
    with mss.mss() as sct:
        while True:
            if keyboard.is_pressed('q'):
                print("Card checker stopped by user.")
                break

            # Capture the card region once
            screenshot = sct.grab(REGION)
            frame = np.array(screenshot)
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            with elixir_lock:
                current_elixir = Elixir

            for card_img, cost in card_costs.items():
                card_path = os.path.join(cards_folder_dir, card_img)
                template = cv2.imread(card_path, cv2.IMREAD_GRAYSCALE)

                if template is None or template.shape[0] == 0 or template.shape[1] == 0:
                    continue

                if template.shape[0] > frame_gray.shape[0] or template.shape[1] > frame_gray.shape[1]:
                    continue

                result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val >= 0.75 and current_elixir >= cost:
                    print(f"Playable: {card_img} (cost: {cost}) | Elixir: {current_elixir} | Confidence: {max_val:.2f}")

            time.sleep(0.1)


def play_card(card_name, location, elixir_cost):
    global Elixir
    pyautogui.click(location.x, location.y)  # Click card
    time.sleep(0.1)
    bot_memory["played_cards"].append(card_name)
    print(bot_memory["played_cards"])
    print(f"[BOT] Played {card_name}, Remaining Elixir: {Elixir}")


def bot_brain_loop():
    while True:
        if keyboard.is_pressed('q'):
            print("Bot brain stopped.")
            break

        with elixir_lock:
            current_elixir = Elixir

        playable_cards = []
        priority_playables = []
        combo_playables = []

        # Screenshot once
        with mss.mss() as sct:
            screenshot = sct.grab(REGION)
            frame = np.array(screenshot)
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            for card_img, cost in card_costs.items():
                card_path = os.path.join(cards_folder_dir, card_img)
                template = cv2.imread(card_path, cv2.IMREAD_GRAYSCALE)

                if template is None:
                    continue

                result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val >= 0.75 and current_elixir >= cost:
                    center_x = max_loc[0] + REGION["left"] + template.shape[1] // 2
                    center_y = max_loc[1] + REGION["top"] + template.shape[0] // 2
                    center = pyautogui.Point(center_x, center_y)
                    card_tuple = (card_img, center, cost)

                    # === Check if this card is part of a combo that is not yet completed ===
                    is_combo_card = False
                    for combo in card_combos:
                        combo_set = set(combo)
                        played_set = set(bot_memory["played_cards"])
                        missing_cards = combo_set - played_set
                        if card_img in missing_cards:
                            combo_playables.append(card_tuple)
                            is_combo_card = True
                            break

                    if not is_combo_card:
                        if card_img in priority_cards:
                            priority_playables.append(card_tuple)
                        else:
                            playable_cards.append(card_tuple)

        # === Play a missing combo card if available ===
        for card_img, center, cost in combo_playables:
            with elixir_lock:
                current_elixir = Elixir
            if current_elixir >= cost:
                play_card(card_img, center, cost)
                time.sleep(0.5)
                break

        else:
            # === Play a priority card ===
            for card_img, center, cost in priority_playables:
                with elixir_lock:
                    current_elixir = Elixir
                if current_elixir >= cost:
                    play_card(card_img, center, cost)
                    time.sleep(0.5)
                    break

            else:
                # === Play a regular card ===
                for card_img, center, cost in playable_cards:
                    with elixir_lock:
                        current_elixir = Elixir
                    if current_elixir >= cost:
                        play_card(card_img, center, cost)
                        time.sleep(0.5)
                        break

        time.sleep(1.5)






def check_and_click_buttons(debounce_seconds=3):
    last_click_time = 0
    buttons = ["PlayAgainButton.png", "QuitButton.png", "BackButton.png", "BattleButton.png"]
    specialbutton = "LuckyDrop.png"

    while True:
        if keyboard.is_pressed('q'):
            print("Button checker stopped by user.")
            break

        current_time = time.time()
        if current_time - last_click_time < debounce_seconds:
            time.sleep(0.1)
            continue

        # Check for special button (LuckyDrop)
        special_path = os.path.join(properties_folder_dir, specialbutton)
        try:
            special_location = pyautogui.locateCenterOnScreen(
                special_path,
                confidence=0.9,
                grayscale=True
            )
            if special_location:
                print(f"[BOT] Detected special button {specialbutton} at {special_location}")
                for _ in range(5):
                    pyautogui.click(special_location)
                    time.sleep(0.5)
                time.sleep(3)
                pyautogui.mouseDown(button='left', x=special_location.x, y=special_location.y)
                pyautogui.mouseUp(button='left', x=special_location.x, y=special_location.y)
                print(f"[BOT] Finished special button press sequence for {specialbutton}")
                last_click_time = time.time()
                continue  # Skip checking other buttons this cycle
        except pyautogui.ImageNotFoundException:
            pass

        # Check normal buttons
        for button_name in buttons:
            button_path = os.path.join(properties_folder_dir, button_name)
            try:
                location = pyautogui.locateCenterOnScreen(
                    button_path,
                    confidence=0.9,
                    grayscale=True
                )
                if location:
                    bot_memory["played_cards"].clear()
                    pyautogui.click(location)
                    print(f"[BOT] Clicked {button_name} at {location}")
                    last_click_time = time.time()
                    break  # Click only one per loop
            except pyautogui.ImageNotFoundException:
                pass

        time.sleep(0.1)





# === Launch Threads ===
elixir_thread = threading.Thread(target=elixir_detector_loop)
elixir_thread.start()

# Optional: uncomment when you want card detection
playable_thread = threading.Thread(target=CheckPlayableCards)
playable_thread.start()

#bot brain
bot_thread = threading.Thread(target=bot_brain_loop)
bot_thread.start()

# Button clicker thread for Play Again / Quit
button_check_thread = threading.Thread(target=check_and_click_buttons)
button_check_thread.start()
