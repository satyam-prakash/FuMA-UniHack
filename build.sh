#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Build React frontend
cd member3/frontend
npm install
npm run build
cd ../..
