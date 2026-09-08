"""OpenCV-based visual audit layer.

This module implements the project's current visual path:

1. Decode submitted Logo Base64.
2. Use OpenCV to extract explainable visual features.
3. Return frontend-compatible radar data and review-only visual risk signals.

It deliberately does not claim legal-grade image similarity or final confusion
judgment. The output is a visual screening signal for human/legal review.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from app.services.rule_repository import build_hit_rule, build_law_reference, get_rule


HIGH_RISK_VISUAL_TERMS = ("四叶", "花卉", "老花", "monogram", "lv", "双c", "双C")


@dataclass(frozen=True)
class VisualFeatures:
    geometry_score: int
    color_score: int
    edge_density_score: int
    symmetry_score: int
    center_score: int
    review_score: int
    dominant_color_count: int
    contour_count: int


def _safe_decode_logo(logo: str) -> bytes:
    """Decode pure Base64 or data URL image payload."""

    if not logo:
        return b""
    payload = logo.split(",", 1)[1] if "," in logo and "base64" in logo[:50] else logo
    try:
        return base64.b64decode(payload, validate=False)
    except Exception:
        return b""


def _decode_image(logo: str) -> np.ndarray | None:
    """Decode logo bytes into an OpenCV BGR image."""

    logo_bytes = _safe_decode_logo(logo)
    if not logo_bytes:
        return None

    buffer = np.frombuffer(logo_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        return None
    return image


def _resize_for_analysis(image: np.ndarray, max_size: int = 256) -> np.ndarray:
    """Resize large images for deterministic and fast analysis."""

    height, width = image.shape[:2]
    scale = min(max_size / max(height, width), 1.0)
    if scale >= 1.0:
        return image
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def _score_edges(gray: np.ndarray) -> tuple[int, np.ndarray]:
    edges = cv2.Canny(gray, 80, 160)
    density = float(np.count_nonzero(edges)) / float(edges.size)
    return int(np.clip(round(density * 500), 0, 100)), edges


def _score_contours(edges: np.ndarray, image_area: int) -> tuple[int, int]:
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant = [contour for contour in contours if cv2.contourArea(contour) >= max(8, image_area * 0.001)]
    contour_count = len(significant)

    if not significant:
        return 10, 0

    perimeter_sum = sum(cv2.arcLength(contour, True) for contour in significant)
    geometry_score = int(np.clip(round((contour_count * 9) + (perimeter_sum / max(image_area, 1) * 900)), 15, 100))
    return geometry_score, contour_count


def _score_colors(image: np.ndarray) -> tuple[int, int]:
    small = cv2.resize(image, (64, 64), interpolation=cv2.INTER_AREA)
    quantized = (small // 32).reshape(-1, 3)
    colors, counts = np.unique(quantized, axis=0, return_counts=True)
    significant_colors = int(np.count_nonzero(counts >= max(12, int(quantized.shape[0] * 0.01))))
    color_score = int(np.clip(round(significant_colors * 12), 10, 100))
    return color_score, significant_colors


def _score_symmetry(gray: np.ndarray) -> int:
    height, width = gray.shape[:2]
    crop_width = min(width // 2, width - width // 2)
    if crop_width <= 0:
        return 0

    left = gray[:, :crop_width]
    right = gray[:, width - crop_width :]
    right_flipped = cv2.flip(right, 1)
    diff = cv2.absdiff(left, right_flipped)
    similarity = 1.0 - (float(np.mean(diff)) / 255.0)
    return int(np.clip(round(similarity * 100), 0, 100))


def _score_center(edges: np.ndarray) -> int:
    ys, xs = np.nonzero(edges)
    if len(xs) == 0 or len(ys) == 0:
        return 0

    height, width = edges.shape[:2]
    center_x = float(np.mean(xs))
    center_y = float(np.mean(ys))
    offset_x = abs(center_x - width / 2) / max(width / 2, 1)
    offset_y = abs(center_y - height / 2) / max(height / 2, 1)
    centeredness = 1.0 - min(1.0, (offset_x + offset_y) / 2)
    return int(np.clip(round(centeredness * 100), 0, 100))


def extract_visual_features(image: np.ndarray) -> VisualFeatures:
    """Extract explainable OpenCV features for the report radar chart."""

    resized = _resize_for_analysis(image)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    edge_density_score, edges = _score_edges(gray)
    geometry_score, contour_count = _score_contours(edges, int(gray.size))
    color_score, dominant_color_count = _score_colors(resized)
    symmetry_score = _score_symmetry(gray)
    center_score = _score_center(edges)

    review_score = int(
        np.clip(
            round(
                geometry_score * 0.24
                + edge_density_score * 0.18
                + symmetry_score * 0.24
                + center_score * 0.18
                + color_score * 0.16
            ),
            0,
            100,
        )
    )

    return VisualFeatures(
        geometry_score=geometry_score,
        color_score=color_score,
        edge_density_score=edge_density_score,
        symmetry_score=symmetry_score,
        center_score=center_score,
        review_score=review_score,
        dominant_color_count=dominant_color_count,
        contour_count=contour_count,
    )


def _radar_data(features: VisualFeatures) -> list[dict[str, int | str]]:
    return [
        {"dimension": "几何轮廓", "target": features.geometry_score, "benchmark": 72},
        {"dimension": "色彩构成", "target": features.color_score, "benchmark": 60},
        {"dimension": "线条密度", "target": features.edge_density_score, "benchmark": 65},
        {"dimension": "对称性", "target": features.symmetry_score, "benchmark": 70},
        {"dimension": "视觉重心", "target": features.center_score, "benchmark": 68},
    ]


def _contains_high_risk_visual_terms(req: dict[str, Any]) -> bool:
    text = " ".join(
        str(req.get(key) or "")
        for key in ("brandName", "englishName", "goodsServices", "businessDescription")
    ).lower()
    return any(keyword.lower() in text for keyword in HIGH_RISK_VISUAL_TERMS)


def run_vision_agent(req: dict[str, Any]) -> dict[str, Any]:
    """Run OpenCV feature extraction and return frontend-compatible visual data."""

    image = _decode_image(str(req.get("logo") or ""))
    if image is None:
        rule = get_rule("VN-INFO-004")
        note = "Logo 图片无法被 OpenCV 解码，可能是空文件、损坏文件或当前不支持的 SVG；视觉判断需人工复核。"
        return {
            "hitRules": [build_hit_rule(rule, applicable=True, note=note, similarity_type="图像解码失败", similarity_score=45)],
            "references": [build_law_reference(rule, note)],
            "radarData": [
                {"dimension": "几何轮廓", "target": 0, "benchmark": 72},
                {"dimension": "色彩构成", "target": 0, "benchmark": 60},
                {"dimension": "线条密度", "target": 0, "benchmark": 65},
                {"dimension": "对称性", "target": 0, "benchmark": 70},
                {"dimension": "视觉重心", "target": 0, "benchmark": 68},
            ],
            "matchedBrands": [],
        }

    features = extract_visual_features(image)
    radar_data = _radar_data(features)
    high_risk_motif = _contains_high_risk_visual_terms(req)

    hit_rules: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    matched_brands: list[dict[str, Any]] = []

    if features.review_score >= 70 or high_risk_motif:
        rule = get_rule("VN-INFO-004")
        if high_risk_motif:
            note = (
                "输入描述含四叶花卉、老花、LV 或双C等高风险视觉线索；"
                "OpenCV 已完成图形结构特征提取，当前结果仅作为视觉相似候选和人工复核入口。"
            )
            similarity_score = max(features.review_score, 60)
        else:
            note = (
                f"OpenCV 检测到图形具有较高结构化视觉特征："
                f"轮廓复杂度 {features.geometry_score}/100、对称性 {features.symmetry_score}/100、"
                f"视觉重心 {features.center_score}/100。该结果仅提示视觉复核优先级，不构成混淆近似结论。"
            )
            similarity_score = features.review_score

        hit_rules.append(
            build_hit_rule(
                rule,
                applicable=True,
                note=note,
                similarity_type="OpenCV视觉相似候选",
                similarity_score=similarity_score,
            )
        )
        references.append(build_law_reference(rule, note))
        matched_brands.append(
            {
                "name": "OpenCV视觉复核候选",
                "thumbnailUrl": "",
                "matchScore": similarity_score,
            }
        )

    return {
        "hitRules": hit_rules,
        "references": references,
        "radarData": radar_data,
        "matchedBrands": matched_brands,
    }
