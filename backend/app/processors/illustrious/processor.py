"""
Illustrious SDXL image processor.

Resolution : ×8 multiples, min side 768 px
"""
from ..registry import register
from ..shared.image_processor import ImageProcessor


@register("ILLUSTRIOUS_SDXL")
class IllustriousProcessor(ImageProcessor):
    model_id            = "ILLUSTRIOUS_SDXL"
    resolution_multiple = 8
    min_side            = 768
    model_tag           = "illustrious"
