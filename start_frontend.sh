#!/bin/bash
# Start frontend directly without turbo
cd "$(dirname "$0")/apps/frontend"
npx next dev --port 3000
