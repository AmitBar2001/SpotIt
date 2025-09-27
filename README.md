---
title: SpotIt
emoji: 🚀
colorFrom: pink
colorTo: purple
sdk: docker
pinned: false
license: apache-2.0
short_description: Can you SpotIt?
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference


## Local Development

python 3.11

in project root directory:
run 'python -m venv venv'

open a new powershell terminal and see that it runs it's activate script
CTRL + SHIFT + P  -> select python interpreter -> choose the one inside venv

run 'pip install -r ./requirements-base.txt'
run 'pip install -r ./requirements.txt'

checkout the .env.example and make your own .env with the neccessary secrets needed to run certain features