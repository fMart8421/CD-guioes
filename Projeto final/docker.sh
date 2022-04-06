#!/bin/sh

if [[ -n $( docker ps -a -q) ]];then
  docker stop $( docker ps -a -q)
  docker rm $( docker ps -a -q)
fi


for (( i=0; i<3; i++ ));do
 setsid --fork gnome-terminal -x bash -c "bash runDocker.sh \"Worker\"$i ; read"
done