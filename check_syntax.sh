#!/bin/bash
find -name "*.py" | xargs -I % pyflakes %
