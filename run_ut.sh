#!/bin/bash
ut_path=$1
PYTHONPATH=.:main python3 -m pytest -s $ut_path
