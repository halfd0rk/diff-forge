"""
FLUX.2 klein image processors (4B and 9B share identical constraints).

Resolution : ×16 multiples, min side 512 px
"""
from ..registry import register
from ..shared.image_processor import ImageProcessor


@register("FLUX2_4B")
class FLUX2Processor4B(ImageProcessor):
    model_id            = "FLUX2_4B"
    resolution_multiple = 16
    min_side            = 512
    model_tag           = "flux2_4b"


@register("FLUX2_9B")
class FLUX2Processor9B(ImageProcessor):
    model_id            = "FLUX2_9B"
    resolution_multiple = 16
    min_side            = 512
    model_tag           = "flux2_9b"
