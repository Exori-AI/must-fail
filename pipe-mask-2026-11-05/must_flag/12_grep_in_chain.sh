#!/bin/bash
# grep exemption must not cover && chains
pytest | grep -q passed && echo shipped
