# axiom_py doesnt ship with types so we need to ignore type errors for imports from that package
import os

import axiom_py  # type: ignore[import-untyped]
from axiom_py.logging import AxiomHandler  # type: ignore[import-untyped]
import logging


def setup_logger():
    logger = logging.getLogger("wide_event")
    logger.setLevel(logging.INFO)

    token = os.environ.get("AXIOM_INGEST_TOKEN")
    dataset = os.environ.get("AXIOM_INGEST_DATASET")

    if token and dataset:
        client = axiom_py.Client(token)
        handler = AxiomHandler(client, dataset=dataset)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
