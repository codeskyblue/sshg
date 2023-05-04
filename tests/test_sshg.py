#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Created on Thu May 04 2023 11:35:28 by codeskyblue
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sshg import password_decorder


def test_password_decorder():
    assert password_decorder(123) == "123"
    assert password_decorder("123") == "123"