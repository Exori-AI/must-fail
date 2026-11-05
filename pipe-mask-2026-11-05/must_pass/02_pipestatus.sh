#!/bin/bash
pytest | tail -5
rc=${PIPESTATUS[0]}
exit $rc
