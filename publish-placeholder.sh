#!/bin/zsh
# Reserve "genui" on PyPI with a placeholder 0.0.1. Token is read from the macOS Keychain.
set -e
TOKEN="$(security find-generic-password -s genui-pypi -w)"
cd /tmp/genui-placeholder && uv publish --token "$TOKEN"
