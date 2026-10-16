"""Generate and verify the public ASEAN teacher-experience QR code."""

from pathlib import Path

import cv2


EXPERIENCE_URL = "http://154.40.45.149/asean-legal/#/experience"
OUTPUT = Path(__file__).resolve().parents[1] / "public" / "teacher-experience-qr.png"


def main() -> None:
    params = cv2.QRCodeEncoder_Params()
    params.correction_level = cv2.QRCodeEncoder_CORRECT_LEVEL_M
    encoder = cv2.QRCodeEncoder_create(params)
    qr = encoder.encode(EXPERIENCE_URL)
    qr = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    qr = cv2.resize(qr, None, fx=12, fy=12, interpolation=cv2.INTER_NEAREST)
    if not cv2.imwrite(str(OUTPUT), qr):
        raise RuntimeError(f"Could not write {OUTPUT}")
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(qr)
    if decoded != EXPERIENCE_URL:
        raise RuntimeError(f"QR verification failed: {decoded!r}")
    print(f"verified {decoded} -> {OUTPUT}")


if __name__ == "__main__":
    main()
