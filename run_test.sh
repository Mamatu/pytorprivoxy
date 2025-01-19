#!/bin/bash
ut_path=$1
PYTHONPATH=.:pylibcommons python3 -m pytest -s $ut_path
