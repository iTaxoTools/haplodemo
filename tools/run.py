#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Launch the haplodemo GUI"""

import multiprocessing

from itaxotools.haplodemo.__main__ import run

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
