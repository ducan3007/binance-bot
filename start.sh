#!/bin/bash
export $(sed 's/#.*//g' .env | xargs)

fastapi run main.py --host=localhost