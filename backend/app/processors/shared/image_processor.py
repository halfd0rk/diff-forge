"""
Base PIL image processor for still-image model fine-tuning.

Subclasses set resolution_multiple, min_side, and model_tag,
then register under their model IDs via @register.
"""
from __future__ import annotations

import collections
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from ..base import VideoProcessor, ProcessorInput, ProcessorOutput, SegmentOutput
from ..ltx.steps.resolution_norm import compute_target_resolution

logger = logging.getLogger(__name__)

try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    _LANCZOS = Image.LANCZOS  # type: ignore[attr-defined]


class ImageProcessor(VideoProcessor):
    """
    PIL-based processor for still image models (FLUX.2, Illustrious, etc.).

    Resizes each image to the nearest resolution that satisfies the model's
    multiple constraint and minimum side length, using aspect-ratio-preserving
    letterbox + background-colour padding.

    Output is always PNG (lossless, universally supported by PIL).
    """

    resolution_multiple: int = 16
    min_side: int = 512
    model_tag: str = "img"

    supported_extensions = {
        ".jpg", ".jpeg", ".png", ".bmp",
        ".tif", ".tiff", ".webp", ".avif",
    }

    def process(self, inp: ProcessorInput) -> ProcessorOutput:
        cfg  = inp.config
        prog = inp.on_progress or (lambda p, m: None)
        tag  = self.model_tag.upper()

        prog(5, "Opening image…")
        img = Image.open(inp.file_path).convert("RGB")
        orig_w, orig_h = img.size
        print(f"[{tag}] Input: {inp.file_path.name}  {orig_w}×{orig_h}")

        # ── Target resolution ─────────────────────────────────────────────────
        prog(20, "Computing target resolution…")
        target_w, target_h = compute_target_resolution(
            orig_w, orig_h,
            multiple=self.resolution_multiple,
            min_side=self.min_side,
            mode=cfg.resolution.mode.value,
            manual_w=cfg.resolution.width,
            manual_h=cfg.resolution.height,
        )

        if not cfg.apply_resolution:
            target_w, target_h = orig_w, orig_h

        print(f"[{tag}] Resolution: {orig_w}×{orig_h} → {target_w}×{target_h}")
        prog(40, f"Target: {target_w}×{target_h}")

        # ── Resize with letterbox padding ─────────────────────────────────────
        prog(60, "Resizing…")
        if orig_w != target_w or orig_h != target_h:
            scale  = min(target_w / orig_w, target_h / orig_h)
            new_w  = min(target_w, int(round(orig_w * scale)))
            new_h  = min(target_h, int(round(orig_h * scale)))
            resized = img.resize((new_w, new_h), _LANCZOS)

            pad_color = _sample_bg(img)
            canvas = Image.new("RGB", (target_w, target_h), pad_color)
            canvas.paste(resized, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        else:
            canvas = img

        # ── Save as PNG ───────────────────────────────────────────────────────
        prog(80, "Saving…")
        out_path = inp.file_path.parent / f"{inp.file_path.stem}_{self.model_tag}.png"
        canvas.save(out_path, "PNG")
        print(f"[{tag}] Saved: {out_path.name}  ({out_path.stat().st_size // 1024} KB)")

        prog(100, f"Done — {target_w}×{target_h}")
        return ProcessorOutput(segments=[
            SegmentOutput(
                path=out_path,
                width=target_w,
                height=target_h,
                frame_count=1,
                fps=1.0,
                duration_secs=1.0,
                segment_index=0,
                start_secs=0.0,
                end_secs=1.0,
            )
        ])


def _sample_bg(img: Image.Image) -> tuple[int, int, int]:
    """Most common border pixel colour — used as letterbox fill."""
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    border = (
        list(map(tuple, arr[0, :, :3].tolist())) +
        list(map(tuple, arr[-1, :, :3].tolist())) +
        list(map(tuple, arr[1:-1, 0, :3].tolist())) +
        list(map(tuple, arr[1:-1, -1, :3].tolist()))
    )
    return collections.Counter(border).most_common(1)[0][0]  # type: ignore[return-value]
