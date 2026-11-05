#!/bin/bash
if [ $(cat /etc/hostname | wc -l) -gt 0 ]; then echo has-lines; fi
true
