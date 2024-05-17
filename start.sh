#!/bin/bash
export $(sed 's/#.*//g' .env | xargs)
fastapi dev main.py