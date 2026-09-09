import cv2
import numpy as np
import time
import HandTracking as ht
import autopy
import screen_brightness_control as sbc
import pyautogui
import math

pTime = 0
width, height = pyautogui.size()
frameR = 280
smoothening = 7         
prev_x, prev_y = 0, 0
curr_x, curr_y = 0, 0
move_multiplier = 100

click_cooldown = 0
click_delay = 0.3

brightness_cooldown = 0
brightness_delay = 0.2

scroll_sensitivity = 0.5   # pixels -> wheel clicks
scroll_deadzone = 4        # ignore tiny hand jitter
scroll_ema_alpha = 0.3     # 0 = very smooth, 1 = instant/raw
smoothed_scroll_delta = 0

scrolling = False
scroll_anchor_x, scroll_anchor_y = 0, 0
prev_scroll_x, prev_scroll_y = 0, 0

x_scroll_point, y_scroll_point = 0, 0
y_diff = 0
last_y_diff = 0

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
print("- Index + Middle finger up (pinch): Left Click")
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
            x3 = np.interp(x1, (frameR, width - frameR), (0, screen_width))
            y3 = np.interp(y1, (frameR, height - frameR), (0, screen_height))

            curr_x = prev_x + (x3 - prev_x) / smoothening
            curr_y = prev_y + (y3 - prev_y) / smoothening

            try:
                autopy.mouse.move(curr_x, curr_y)

            except Exception as e:
                pass

            prev_x, prev_y = curr_x, curr_y

            # --- Left click / drag ---
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

            # # --- Left click(old) ---
            # length, img, lineInfo = detector.findDistance(4, 8, img, draw=True, r=5, t=1)
            # length2, img2, lineInfo2 = detector.findDistance(9, 13, img, draw=False, r=5, t=1)
            #
            # if length <= 60:
            #     cv2.circle(img, (lineInfo[4], lineInfo[5]),15, (0, 255, 0), cv2.FILLED)
            #
            #     current_time = time.time()
            #
            #     autopy.mouse.toggle(autopy.mouse.Button.LEFT, True)
            #
            #     # if current_time - click_cooldown > click_delay:
            #     #     try:
            #     #         autopy.mouse.click()
            #     #         click_cooldown = current_time
            #     #         cv2.putText(img, "LEFT CLICK", (50, 50),
            #     #                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
            #     #     except Exception as e:
            #     #         pass
            #
            # else:
            #     autopy.mouse.toggle(autopy.mouse.Button.LEFT, False)

        # --- Right click ---
            length, img, lineInfo = detector.findDistance(4, 12, img, draw=True, r=5, t=1)
            length2, img2, lineInfo2 = detector.findDistance(9, 13, img, draw=False, r=5, t=1)

            if length <= 44:
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 0, 255), cv2.FILLED)

                current_time = time.time()

                # pyautogui.mouseDown(button='right')
                # right_clicking = True
                if current_time - click_cooldown > click_delay:
                    try:
                        autopy.mouse.click(autopy.mouse.Button.RIGHT)
                        click_cooldown = current_time
                        cv2.putText(img, "RIGHT CLICK", (50, 50),
                                   cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                    except Exception as e:
                        pass

            # --- Enter scroll (thumb + ring pinch) ---
            scroll_len, img, scroll_info = detector.findDistance(4, 16, img, draw=True, r=5, t=1)
            if scroll_len <= 64:
                current_time = time.time()
                if current_time - click_cooldown > click_delay:
                    try:
                        scrolling = True
                        scroll_anchor_x, scroll_anchor_y = x_thumb, y_thumb
                        prev_scroll_x, prev_scroll_y = x_thumb, y_thumb
                        smoothed_scroll_delta = 0
                        click_cooldown = current_time
                        cv2.putText(img, "SCROLL GRAB", (50, 50),
                                cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                    except Exception as e:
                        pass

                else:
                    length, img, lineInfo = detector.findDistance(4, 16, img, draw=True, r=5, t=1)
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (255, 0, 0), cv2.FILLED)

                    if length > 64:
                        scrolling = False
                        smoothed_scroll_delta = 0
                    else:
                        # 1. raw movement since last frame
                        raw_delta = y_thumb - prev_scroll_y
                        prev_scroll_x, prev_scroll_y = x_thumb, y_thumb

                        # 2. deadzone
                        if abs(raw_delta) < scroll_deadzone:
                            raw_delta = 0

                        # 3. exponential moving average smooth
                        smoothed_scroll_delta = (
                                scroll_ema_alpha * raw_delta +
                                (1 - scroll_ema_alpha) * smoothed_scroll_delta
                        )

                        # 4. apply sensitivity and flip sign
                        #    hand moves down in image (y increases) -> scroll down
                        scroll_amount = int(-smoothed_scroll_delta * scroll_sensitivity)

                        # 5. scroll only if there's meaningful movement
                        if abs(scroll_amount) > 0:
                            pyautogui.scroll(scroll_amount)

                        cv2.putText(img, 'SCROLLING', (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                        cv2.putText(img, f'Delta:{scroll_amount}', (50, 80), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                        cv2.circle(img, (scroll_anchor_x, scroll_anchor_y), 5, (255, 0, 0), cv2.FILLED)
                        cv2.line(img, (scroll_anchor_x, scroll_anchor_y), (x_thumb, y_thumb), (255, 0, 0), 2)

        # --- Scroll(old ---

        #     length, img, lineInfo = detector.findDistance(4, 16, img, draw=True, r=5, t=1)
        #     length2, img2, lineInfo2 = detector.findDistance(9, 13, img, draw=False, r=5, t=1)
        #
        #     if length <= 64 and not scrolling:
        #         cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (255, 0, 0), cv2.FILLED)
        #
        #         current_time = time.time()
        #         if current_time - click_cooldown > click_delay:
        #             try:
        #                 scrolling = True
        #                 x_scroll_point, y_scroll_point = x_thumb, y_thumb
        #                 click_cooldown = current_time
        #                 cv2.putText(img, "RIGHT CLICK", (50, 50),
        #                         cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
        #             except Exception as e:
        #                 pass
        # else:
        #     length, img, lineInfo = detector.findDistance(4, 16, img, draw=True, r=5, t=1)
        #     cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (255, 0, 0), cv2.FILLED)
        #     if length > 64:
        #         scrolling = False
        #     else:
        #         if y_thumb > y_scroll_point:
        #             y_diff = y_thumb - y_scroll_point
        #         elif y_thumb < y_scroll_point:
        #             y_diff = y_scroll_point - y_thumb
        #         # y_diff = int(y_diff)
        #         if y_diff > 0:
        #             # if y_diff < last_y_diff:
        #             #     y_diff = last_y_diff - y_diff
        #             # elif y_diff > last_y_diff:
        #             #     y_diff = y_diff - last_y_diff
        #             if last_y_diff < y_diff:
        #                 y_diff = math.hypot(y_thumb - y_scroll_point)
        #             else:
        #                 y_diff = math.hypot(y_thumb - y_scroll_point)
        #                 y_diff = y_diff * -1
        #         elif y_diff < 0:
        #             # if y_diff < last_y_diff:
        #             #     y_diff = last_y_diff - y_diff
        #             # elif y_diff > last_y_diff:
        #             #     y_diff = y_diff - last_y_diff
        #             if last_y_diff > y_diff:
        #                 y_diff = math.hypot(y_thumb - y_scroll_point)
        #                 y_diff = y_diff * -1
        #             else:
        #                 y_diff = math.hypot(y_thumb - y_scroll_point)
        #
        #         y_diff = y_diff // 10
        #         pyautogui.scroll(y_diff)
        #
        #     cv2.putText(img, f'SCROLLING', (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
        #     cv2.putText(img, f'Diff:{y_diff}', (50, 80), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
        #     cv2.circle(img, (x_scroll_point, y_scroll_point), 5, (255, 0, 0), cv2.FILLED)
        #     cv2.line(img, (x_scroll_point, y_scroll_point), (x_thumb, y_thumb), (255, 0, 0), 2)
        #     if y_thumb > y_scroll_point:
        #         y_diff = y_thumb - y_scroll_point
        #     elif y_thumb < y_scroll_point:
        #         y_diff = y_scroll_point - y_thumb
        #     last_y_diff = y_diff

    current_time = time.time()

        # if fingers == [1, 1, 1, 1, 1]:
        #     if current_time - brightness_cooldown > brightness_delay:
        #         try:
        #             current_brightness = sbc.get_brightness()[0]
        #             new_brightness = min(100, current_brightness + 5)
        #             sbc.set_brightness(new_brightness)
        #             brightness_cooldown = current_time
        #             cv2.putText(img, f"BRIGHTNESS UP: {new_brightness}%", (50, 50),
        #                        cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 3)
        #         except Exception as e:
        #             cv2.putText(img, "Brightness control error", (50, 50),
        #                        cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
        #
        # if fingers == [0, 0, 0, 0, 0]:
        #     if current_time - brightness_cooldown > brightness_delay:
        #         break

    cTime = time.time()
    fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
    pTime = cTime
    # length, img, lineInfo = detector.findDistance(5, 17, img, draw=True, r=10, t=2)
    # cv2.putText(img, "Distance Measurement In millimeters" + length, (width - 150, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
    cv2.putText(img, f'FPS: {int(fps)}', (width - 150, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

    cv2.imshow("Virtual Mouse", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Virtual Mouse Stopped!")