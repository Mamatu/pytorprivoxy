#!/bin/bash
PYTHONPATH=.:./pylibcommons python3 -m pytest -s -vv $(find -name "test_*.py" -not -path "./pylibcommons/*") --full-trace
