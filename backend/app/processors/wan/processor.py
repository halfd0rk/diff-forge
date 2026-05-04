"""
WAN video processor.

Frame rule : 4n+1  (1, 5, 9, 13, …, 597)
Resolution : ×32 multiples, min side 32 px
"""
from __future__ import annotations

import math
import logging

from ..base import VideoProcessor, ProcessorInput, ProcessorOutput, SegmentOutput
from ..registry import register
# Re-use the model-agnostic I/O helpers and normalisation steps from LTX.
from ..ltx.processor import _probe, _decode, _encode  # noqa: PLC2701
from ..ltx.steps.frame_norm import resample_bresenham
from ..ltx.steps.resolution_norm import compute_target_resolution, normalize_resolution

logger = logging.getLogger(__name__)

_RESOLUTION_MULTIPLE = 32
_RESOLUTION_MIN_SIDE = 32
_FRAME_MIN = 1
_FRAME_MAX = 600


def _next_4n1(n: int) -> int:
    """Smallest frame count >= n that satisfies 4n+1."""
    if n <= _FRAME_MIN:
        return _FRAME_MIN
    k = math.ceil((n - 1) / 4)
    return min(4 * k + 1, _FRAME_MAX)


def _log(msg: str) -> None:
    print(f"[WAN] {msg}", flush=True)


@register("WAN")
class WANProcessor(VideoProcessor):
    model_id = "WAN"
    supported_extensions = {".mp4", ".mov", ".avi", ".webm", ".gif"}

    def process(self, inp: ProcessorInput) -> ProcessorOutput:
        cfg  = inp.config
        prog = inp.on_progress or (lambda p, m: None)

        # ── 1. Probe ──────────────────────────────────────────────────────────
        prog(3, "Probing video…")
        orig_w, orig_h, fps = _probe(inp.file_path)
        _log(f"Probe: {orig_w}×{orig_h} @ {fps:.3f} fps")

        # ── 2. Decode ─────────────────────────────────────────────────────────
        prog(10, "Decoding frames…")
        frames = _decode(inp.file_path, orig_w, orig_h)
        _log(f"Decoded {len(frames)} frames")
        prog(30, f"Decoded {len(frames)} frames")

        # ── 3. Target resolution ──────────────────────────────────────────────
        target_w, target_h = compute_target_resolution(
            orig_w, orig_h,
            multiple=_RESOLUTION_MULTIPLE,
            min_side=_RESOLUTION_MIN_SIDE,
            mode=cfg.resolution.mode.value,
            manual_w=cfg.resolution.width,
            manual_h=cfg.resolution.height,
        )
        prog(32, f"Target resolution: {target_w}×{target_h}")

        # ── 4. Segment boundaries ─────────────────────────────────────────────
        total = len(frames)
        split_indices = sorted({
            max(1, min(total - 1, round(t * fps)))
            for t in (cfg.splits or [])
        })
        boundaries   = [0] + split_indices + [total]
        segments_raw = [
            (frames[boundaries[i]: boundaries[i + 1]], boundaries[i], boundaries[i + 1])
            for i in range(len(boundaries) - 1)
            if boundaries[i] < boundaries[i + 1]
        ]
        n_segs = len(segments_raw)
        prog(35, f"{n_segs} segment(s)")

        outputs: list[SegmentOutput] = []

        for seg_idx, (seg_frames, start_fi, end_fi) in enumerate(segments_raw):
            seg_base = 35 + int(seg_idx / n_segs * 60)

            # ── 5. Frame normalisation ────────────────────────────────────────
            src_fc = len(seg_frames)

            if cfg.apply_frames:
                if cfg.frames.mode.value == "strict" and cfg.frames.target is not None:
                    target_fc = cfg.frames.target
                    if target_fc < src_fc:
                        raise ValueError(
                            f"Frame target {target_fc} < source {src_fc}; "
                            "normalisation only adds frames."
                        )
                else:
                    target_fc = _next_4n1(src_fc)

                if target_fc != src_fc:
                    seg_frames = resample_bresenham(seg_frames, target_fc)
            else:
                target_fc = src_fc

            if cfg.frame_deletions:
                delete_set = set(cfg.frame_deletions)
                seg_frames = [f for i, f in enumerate(seg_frames) if i not in delete_set]
                target_fc  = len(seg_frames)

            prog(seg_base + 15, f"Seg {seg_idx + 1}: {target_fc} frames")

            # ── 6. Resolution normalisation ───────────────────────────────────
            if cfg.apply_resolution:
                seg_frames = normalize_resolution(seg_frames, target_w, target_h)

            out_w = target_w if cfg.apply_resolution else orig_w
            out_h = target_h if cfg.apply_resolution else orig_h

            # ── 7. Encode ─────────────────────────────────────────────────────
            suffix   = f"_seg{seg_idx}" if n_segs > 1 else ""
            out_path = inp.file_path.parent / f"{inp.file_path.stem}_wan{suffix}.mp4"
            prog(seg_base + 25, f"Seg {seg_idx + 1}: encoding…")
            _encode(seg_frames, out_path, fps, out_w, out_h)

            outputs.append(SegmentOutput(
                path=out_path,
                width=out_w,   height=out_h,
                frame_count=target_fc,
                fps=fps,
                duration_secs=target_fc / fps,
                segment_index=seg_idx,
                start_secs=start_fi / fps,
                end_secs=end_fi   / fps,
            ))

        prog(100, f"Done — {n_segs} seg(s), {target_w}×{target_h}")
        _log(f"Done: {n_segs} seg(s)  {target_w}×{target_h}  {target_fc}f")
        return ProcessorOutput(segments=outputs)
