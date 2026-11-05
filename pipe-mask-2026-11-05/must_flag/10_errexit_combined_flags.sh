#!/bin/bash
set -eu
mvn test | tail -50
echo shipped
