#!/bin/bash

downloadpath="./videos"
archivepath=$PWD

echo "Enter youtube link:"
read link

echo "Quality (360,480,720,1080...):  "
read quality

echo "  "



if [ ! -d "$downloadpath" ]; then
  echo "Creating directory..."
  mkdir "$downloadpath"
fi


cd "$downloadpath"

yt-dlp -i  -f 'bestvideo[height<='$quality']+bestaudio/best[height<='$quality']' --embed-metadata --all-subs --embed-subs --embed-thumbnail   -o "[%(channel).30s]: %(title).60s [%(upload_date)s].%(ext)s" --download-archive "$archivepath/youtube.archive.txt" "$link"


echo "Finished downloading."
read


