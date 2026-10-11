# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nicolas and the IngeTrazo SubD contributors.
"""SubD — subdivision (Catmull-Clark) modelling for IngeTrazo.

An extension: IngeTrazo calls :func:`setup` when the main window is built.
The interface (``panel.py``) is imported only then, so the geometry modules
(``subdivide``, ``edit``, ``follow``, ``group``, ``ops``) stay pure Python and
can be tested without Qt or IngeTrazo.
"""
__version__ = "1.0"


def setup(app) -> None:
    from .panel import setup as _setup
    _setup(app)
