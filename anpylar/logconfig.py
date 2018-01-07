#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import logging


def logconfig(quiet, verbose):
    if quiet:
        verbose_level = logging.ERROR
    else:
        verbose_level = logging.INFO - verbose * 10  # -> DEBUG

    logging.basicConfig(
        # format="%(levelname)s: %(message)s",
        format="%(message)s",
        level=verbose_level
    )
