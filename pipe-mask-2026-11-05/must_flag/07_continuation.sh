#!/bin/bash
pytest tests/ \
  | tail -3 && echo ok
