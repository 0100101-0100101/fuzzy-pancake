import cv2
import numpy as np
import time
import HandTracking as ht
import autopy
import screen_brightness_control as sbc
import pyautogui

pTime = 0
width, height = pyautogui.size()
frameR = 280
smoothening = 7
prev_x, prev_y = 0, 0
curr_x, curr_y = 0, 0

click_cooldown = 0
click_delay = 0.3

brightness_cooldown = 0
brightness_delay = 0.2

# --- Scroll state ---
scrolling = False
scroll_anchor_x, scroll_anchor_y = 0, 0
prev_scroll_y = 0
scroll_smoothed = 0.0
scroll_sensitivity = 0.8
scroll_deadzone = 3
scroll_alpha = 0.3

left_pinch_start = None
drag_threshold = 0.4   # seconds before a pinch becomes a drag
is_dragging = False

cap = cv2.VideoCapture(1)
cap.set(4, width)
cap.set(4, height)

detector = ht.handDetector(maxHands=1, detectionCon=0.8, trackCon=0.8)
screen_width, screen_height = autopy.screen.size()

print("Virtual Mouse Started!")
print("Controls:")
print("- Index finger up: Move cursor")
print("- Index + Middle finger up (pinch): Left Click / Drag")
print("- Index + Middle + Ring finger up: Right Click")
print("- All 5 fingers open: Increase Brightness")
print("- All fingers closed (fist): Decrease Brightness")
print("- Press 'q' to quit")

while True:
    success, img = cap.read()
    if not success:
        print("Failed to capture frame")
        continue

    img = cv2.flip(img, 1)
    img = detector.findHands(img)
    lmlist, bbox = detector.findPosition(img, draw=False)

    if len(lmlist) != 0:
        x1, y1 = lmlist[4][1:]
        x2, y2 = lmlist[12][1:]
        x3, y3 = lmlist[16][1:]
        x_thumb, y_thumb = lmlist[4][1:]

        fingers = detector.fingersUp()

        if frameR > 0:
            cv2.rectangle(img, (frameR, frameR),
                         (width - frameR, height - frameR),
                         (255, 0, 255), 2)

        if not scrolling:
            # --- Cursor movement ---
            x3 = np.interp(x1, (frameR, width - frameR), (0, screen_width))
            y3 = np.interp(y1, (frameR, height - frameR), (0, screen_height))

            curr_x = prev_x + (x3 - prev_x) / smoothening
            curr_y = prev_y + (y3 - prev_y) / smoothening

            try:
                autopy.mouse.move(curr_x, curr_y)
            except Exception as e:
                pass

            prev_x, prev_y = curr_x, curr_y

            # --- Left click / drag (hold while pinching) ---
            length, img, lineInfo = detector.findDistance(4, 8, img, draw=True, r=5, t=1)

            current_time = time.time()

            if length <= 50:
                if left_pinch_start is None:
                    left_pinch_start = current_time

                pinch_duration = current_time - left_pinch_start

                # After threshold, hold the button for drag/select
                if pinch_duration >= drag_threshold:
                    if not is_dragging:
                        autopy.mouse.toggle(autopy.mouse.Button.LEFT, True)
                        is_dragging = True
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 255, 0), cv2.FILLED)
                    cv2.putText(img, "DRAG", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)

                else:
                    # Visual feedback that a pinch is being held
                    progress = min(pinch_duration / drag_threshold, 1.0)
                    radius = int(5 + 10 * progress)
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), radius, (0, 200, 255), cv2.FILLED)

            else:
                # Release ended
                if is_dragging:
                    autopy.mouse.toggle(autopy.mouse.Button.LEFT, False)
                    is_dragging = False
                elif left_pinch_start is not None:
                    # Short pinch = single click
                    autopy.mouse.click()

                left_pinch_start = None

            # --- Right click ---
            length, img, lineInfo = detector.findDistance(4, 12, img, draw=True, r=5, t=1)
            if length <= 44:
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (255, 255, 0), cv2.FILLED)
                current_time = time.time()
                if current_time - click_cooldown > click_delay:
                    try:
                        autopy.mouse.click(autopy.mouse.Button.RIGHT)
                        click_cooldown = current_time
                        cv2.putText(img, "RIGHT CLICK", (50, 50),
                                   cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                    except Exception as e:
                        pass

            # --- Close Window ---
            length, img, lineInfo = detector.findDistance(4, 20, img, draw=True, r=5, t=1)
            if length <= 50:
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 0, 255), cv2.FILLED)
                current_time = time.time()
                if current_time - click_cooldown > click_delay:
                    try:
                        autopy.key.key_down(autopy.key.Code.COMMAND)
                        autopy.key.key_down(autopy.key.Code.w)
                        autopy.key.key_up(autopy.key.Code.COMMAND)
                        autopy.key.key_up(autopy.key.Code.w)
                        click_cooldown = current_time
                        cv2.putText(img, "CLOSED WINDOW", (50, 50),
                                   cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                    except Exception as e:
                        pass

            # --- Enter scroll mode ---
            scroll_len, img, scroll_info = detector.findDistance(4, 16, img, draw=True, r=5, t=1)
            if scroll_len <= 64:
                current_time = time.time()
                if current_time - click_cooldown > click_delay:
                    scrolling = True
                    scroll_anchor_x = x_thumb
                    scroll_anchor_y = y_thumb
                    prev_scroll_y = y_thumb
                    scroll_smoothed = 0.0
                    click_cooldown = current_time
                    cv2.putText(img, "SCROLL GRAB", (50, 50),
                               cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)

        else:
            # --- Scroll mode ---
            scroll_len, img, scroll_info = detector.findDistance(4, 16, img, draw=True, r=5, t=1)
            cv2.circle(img, (scroll_info[4], scroll_info[5]), 15, (255, 0, 0), cv2.FILLED)
            cv2.line(img, (scroll_anchor_x, scroll_anchor_y),
                    (x_thumb, y_thumb), (255, 0, 0), 2)

            if scroll_len > 64:
                scrolling = False
                scroll_smoothed = 0.0
            else:
                # 1. per-frame movement
                raw_delta = y_thumb - prev_scroll_y
                prev_scroll_y = y_thumb

                # 2. deadzone
                if abs(raw_delta) < scroll_deadzone:
                    raw_delta = 0

                # 3. exponential moving average
                scroll_smoothed = scroll_alpha * raw_delta + (1 - scroll_alpha) * scroll_smoothed

                # 4. scroll amount
                scroll_amount = int(-scroll_smoothed * scroll_sensitivity)
                if scroll_amount != 0:
                    pyautogui.scroll(scroll_amount)

                cv2.putText(img, 'SCROLLING', (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                cv2.putText(img, f'Delta:{scroll_amount}', (50, 80),
                           cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                cv2.circle(img, (scroll_anchor_x, scroll_anchor_y), 5, (255, 0, 0), cv2.FILLED)

    current_time = time.time()

    cTime = time.time()
    fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
    pTime = cTime

    cv2.putText(img, f'FPS: {int(fps)}', (width - 150, 50),
               cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

    cv2.imshow("Virtual Mouse", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Virtual Mouse Stopped!")