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
frameR = 450
smoothening = 7
prev_x, prev_y = 0, 0
curr_x, curr_y = 0, 0
move_multiplier = 0

click_cooldown = 0
click_delay = 0.3

brightness_cooldown = 0
brightness_delay = 0.2

scrolling = False
x_scroll_point, y_scroll_point = 0, 0
y_diff = 0

cam = 1
cap = cv2.VideoCapture(cam)
cap.set(4, width)
cap.set(4, height)

detector = ht.handDetector(maxHands=1, detectionCon=0.8, trackCon=0.8)
screen_width, screen_height = autopy.screen.size()

print("Virtual Mouse Started!")
print("Controls:")
print("- Thumb: Moves cursor")
print("- Index + Middle finger up (pinch): Left Click")
print("- Middle + Ring finger up: Right Click")
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
        length, img, lineInfo = detector.findDistance(5, 17, img, draw=True, r=0, t=1)
        cv2.putText(img, f'Distance {int(length)}', (50, 120), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

        if length <= 90:
            cv2.putText(img, f'Peas rotate your palm', (int(width / 2) - 300, int((height) /2)), cv2.FONT_HERSHEY_PLAIN, 3.5, (0, 0, 255), 2)
            cv2.putText(img, f'to face the screen', (int(width / 2) - 270, int((height /2) + 40)), cv2.FONT_HERSHEY_PLAIN, 3.5, (0, 0, 255), 2)

        else:
            if not scrolling:
                x3 = np.interp(x1, (frameR, width - frameR), (0, screen_width - 100))
                y3 = np.interp(y1, (frameR, height - frameR), (0, screen_height - 100))

                curr_x = prev_x + ((x3 + move_multiplier) - prev_x) / smoothening
                curr_y = prev_y + ((y3 + move_multiplier) - prev_y) / smoothening

                try:
                    autopy.mouse.move(curr_x, curr_y)
                    cv2.circle(img, (x1, y1), 10, (0, 255, 0), cv2.FILLED)

                except Exception as e:
                    pass

                prev_x, prev_y = curr_x, curr_y

                # --- Left click ---
                length, img, lineInfo = detector.findDistance(8, 12, img, draw=True, r=5, t=1)
                length2, img2, lineInfo2 = detector.findDistance(9, 13, img, draw=False, r=5, t=1)

                if length <= length2:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]),
                              15, (0, 255, 0), cv2.FILLED)

                    current_time = time.time()

                    autopy.mouse.toggle(autopy.mouse.Button.LEFT, True)

                else:
                    autopy.mouse.toggle(autopy.mouse.Button.LEFT, False)

                # --- Right click ---
                length, img, lineInfo = detector.findDistance(12, 16, img, draw=True, r=5, t=1)
                length2, img2, lineInfo2 = detector.findDistance(9, 13, img, draw=False, r=5, t=1)

                if length <= length2 - 5:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 0, 255), cv2.FILLED)

                    current_time = time.time()
                    if current_time - click_cooldown > click_delay:
                        try:
                            autopy.mouse.click(autopy.mouse.Button.RIGHT)
                            click_cooldown = current_time
                            cv2.putText(img, "RIGHT CLICK", (50, 50),
                                       cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                        except Exception as e:
                            pass

                current_time = time.time()

                # --- cmd tab ---
                length, img, lineInfo = detector.findDistance(15, 20, img, draw=True, r=5, t=1)
                length2, img2, lineInfo2 = detector.findDistance(13, 17, img, draw=False, r=5, t=1)

                if length <= 90:
                    try:
                        autopy.key.press_key(autopy.key.Code.COMMAND, autopy.key.Code.TAB)
                        click_cooldown = current_time
                        cv2.putText(img, "SWAP TAB", (50, 50),
                                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                    except Exception as e:
                        pass

                # --- Scroll ---
                length, img, lineInfo = detector.findDistance(4, 8, img, draw=True, r=5, t=1)
                length2, img2, lineInfo2 = detector.findDistance(9, 13, img, draw=False, r=5, t=1)

                if length <= 64:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (255, 0, 0), cv2.FILLED)

                    current_time = time.time()
                    if current_time - click_cooldown > click_delay:
                        try:
                            scrolling = True
                            x_scroll_point, y_scroll_point = x_thumb, y_thumb
                            click_cooldown = current_time
                            cv2.putText(img, "RIGHT CLICK", (50, 50),
                                        cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                        except Exception as e:
                            pass

            else:
                length, img, lineInfo = detector.findDistance(4, 8, img, draw=True, r=5, t=1)
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (255, 0, 0), cv2.FILLED)
                if length > 64:
                    scrolling = False
                else:
                    if y_scroll_point > y_thumb:
                        y_diff = math.hypot(x_thumb - y_scroll_point)
                    elif y_scroll_point < y_thumb:
                        y_diff = math.hypot(y_thumb - y_scroll_point)
                        y_diff = y_diff * -1
                    y_diff = y_diff // 5
                    pyautogui.scroll(int(y_diff))

                cv2.putText(img, f'SCROLLING', (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                cv2.putText(img, f'Diff:{int(y_diff)}', (50, 80), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                cv2.circle(img, (x_scroll_point, y_scroll_point), 5, (255, 0, 0), cv2.FILLED)
                cv2.line(img, (x_scroll_point, y_scroll_point), (x_thumb, y_thumb), (255, 0, 0), 2)

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

    fingers = detector.fingersUp()

    # if fingers == [0, 0, 0, 0, 0]:
    #         if current_time - brightness_cooldown > brightness_delay:
    #                 break
    # else:
    #     cv2.putText(img, "No Hand Detected", (50, 50),
    #                cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

    cTime = time.time()
    fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (width - 150, 50), 
               cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

    cv2.imshow("Virtual Mouse", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if cv2.waitKey(2) & 0xFF == ord('c'):
        if cam < 4:
            cam += 1
        else:
            cam = 0
        cap = cv2.VideoCapture(cam)
        cap.set(3, width)
        cap.set(4, height)

cap.release()
cv2.destroyAllWindows()

print("Virtual Mouse Stopped!")