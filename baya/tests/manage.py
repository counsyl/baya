#!/usr/bin/env python
import os
import sys

from django.core import management

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "baya.tests.settings")
    management.execute_from_command_line(sys.argv)
