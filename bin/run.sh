#!/bin/bash
docker stop help-center && docker rm help-center
docker run --name help-center -d --restart="always" help-center
