# -*- coding: utf-8 -*-
"""사용자가 준 브레이크 스킬 스크린샷(원형 일러스트 부분)을 작게 잘라 work/break_img/icons/<이름>.jpg 로 저장.
사용: C:\\build\\jh\\.venv\\Scripts\\python.exe -X utf8 -I crop_break_icons.py  (cv2 필요, 스크린샷은 work/break_img/ref/ 에 복사해 둔다)"""
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "break_ref")  # 인게임 스크린샷 7~11.png(저장소에 없음)
OUT = os.path.join(HERE, "assets", "break_icons")
NAMES = {"7": "특이점 관측", "8": "스타피어서", "9": "큐브 과부하", "10": "행성 정화", "11": "차원 강습"}
SIZE = 168


def main():
    os.makedirs(OUT, exist_ok=True)
    for num, name in NAMES.items():
        a = cv2.imdecode(np.fromfile(os.path.join(REF, num + ".png"), dtype=np.uint8), cv2.IMREAD_COLOR)
        h, w = a.shape[:2]
        cx, cy, r = int(w * 0.5), int(h * 0.37), int(w * 0.30)  # 원형 일러스트 중심/반지름(화면 비율 기준 추정)
        crop = a[max(0, cy - r):cy + r, max(0, cx - r):cx + r]
        crop = cv2.resize(crop, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 82])
        buf.tofile(os.path.join(OUT, name + ".jpg"))
        print(name, len(buf), "bytes")


if __name__ == "__main__":
    main()
