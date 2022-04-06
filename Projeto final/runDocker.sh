#!/bin/sh
DOCKERNAME=${1:-"Worker1"}

 docker build --tag projecto_final . &&  docker run  --name $DOCKERNAME projecto_final