# Import each model package so @register decorators fire at startup.
from .ltx        import LTXProcessor                    # noqa: F401
from .wan        import WANProcessor                    # noqa: F401
from .flux2      import FLUX2Processor4B, FLUX2Processor9B  # noqa: F401
from .illustrious import IllustriousProcessor           # noqa: F401
