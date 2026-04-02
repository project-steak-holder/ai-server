# axiom_py doesnt ship with types so we need to ignore type errors for imports from that package
import os

import axiom_py  # type: ignore[import-untyped]
from axiom_py.logging import AxiomHandler  # type: ignore[import-untyped]
import logging


def setup_logger():
    client = axiom_py.Client(os.environ["AXIOM_INGEST_TOKEN"])
    handler = AxiomHandler(client, dataset=os.environ["AXIOM_INGEST_DATASET"])
    handler.setLevel(logging.INFO)

    # Add the Axiom handler to the Wide Event logger
    logger = logging.getLogger("wide_event")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
