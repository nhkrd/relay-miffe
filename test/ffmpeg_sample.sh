ffmpeg \
-threads 0 -re \
-i hoge.mp4 \
-map 0 -c:a aac -c:v libx264 -b:v:0 1000k -s:v:0 1280x720 -profile:v:0 high \
-frag_duration 1000 -seg_duration 6 \
-adaptation_sets "id=0,streams=v id=1,streams=a" \
-dash_segment_type mp4 \
-window_size 10 \
-streaming 1 \
-preset ultrafast \
-ldash 1 \
-live 1 \
-use_template 1 -use_timeline 0 \
-tune zerolatency \
-f dash \
-method PUT http://xxx.xxx.xxx.xxx:8500/?url=http://xxx.xxx.xxx.xxx:8000/content/manifest.mpd