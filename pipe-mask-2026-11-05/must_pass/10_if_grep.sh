#!/bin/bash
# exemption: grep status is the condition
if pgrep -x sshd | grep -q .; then echo up; fi
