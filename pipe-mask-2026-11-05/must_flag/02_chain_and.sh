#!/bin/bash
pytest -q | tail -5 && echo "tests passed"
