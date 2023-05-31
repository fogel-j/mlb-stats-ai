#!/bin/bash
find /path/to/your/directory -name "mlb_news_*.json" -type f -mtime +5 -exec rm -f {} \;