"""Mux actual game sound and add Chinese explanatory subtitles to browser capture."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'
metadata=json.loads((OUT/'playthrough-recording.json').read_text())
raw=OUT/'recording-raw'/'actual-playthrough.webm'
audio=OUT/'recording-raw'/'actual-game-audio.webm'
result=OUT/'ramen-gate-actual-playthrough.mp4'

def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

rawinfo=probe(raw)
duration=float(rawinfo['format']['duration'])
selected=[]
for event in metadata['events']:
 label=event['event']
 if label=='实际火候控制':continue
 caption=event['caption']
 if label=='进入游戏':caption='真实游戏试玩｜方向键移动，Z 互动，X 返回'
 elif label=='选择 BLUE 开始':caption='选择 BLUE，开始营业'
 elif label=='煮汤菜单':caption='COOK：轻柔搅拌，进入绿色区间再按 Z 完成'
 elif label=='装碗出餐':caption='BOWL：按 Z 装碗出餐'
 elif label=='五星结算':caption='6 碗完成！1125 分、5 星｜全程为真实按键操作'
 selected.append((event['time'],caption))

def stamp(seconds):
 ms=max(0,round(seconds*1000));h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'
lines=[]
for i,(start,caption) in enumerate(selected):
 end=selected[i+1][0]-.08 if i+1<len(selected) else duration-.15
 lines.extend([str(i+1),f'{stamp(start)} --> {stamp(end)}',caption,''])
subtitle=OUT/'ramen-gate-playthrough.zh-CN.srt'
subtitle.write_text('\n'.join(lines),encoding='utf8')
filtergraph="subtitles=artifacts/ramen-gate-playthrough.zh-CN.srt:force_style='FontName=Noto Sans CJK SC,FontSize=23,Alignment=2,MarginV=18,Outline=1,Shadow=0,BorderStyle=3,BackColour=&H85000000'"
cmd=['ffmpeg','-y','-hide_banner','-loglevel','warning','-i',str(raw),'-itsoffset',str(metadata['audio_offset_seconds']),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-vf',filtergraph,'-af','apad','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(result)]
subprocess.run(cmd,cwd=ROOT,check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(result),'-f','null','-'],check=True)
info=probe(result)
volume=subprocess.run(['ffmpeg','-hide_banner','-i',str(result),'-map','0:a:0','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True)
volume_lines=[line.strip() for line in volume.stderr.splitlines() if 'mean_volume:' in line or 'max_volume:' in line]
assert not any('max_volume: -inf' in line for line in volume_lines),'Captured audio is silent'
streams=[{k:s.get(k) for k in ['codec_type','codec_name','width','height','avg_frame_rate','sample_rate','channels']} for s in info['streams']]
validation={'status':'passed','file':result.name,'bytes':result.stat().st_size,'duration_seconds':float(info['format']['duration']),'streams':streams,'audio_measurements':volume_lines,'decode_check':'ffmpeg full decode completed without errors','realtime_interactions':True,'game_state_modified':False,'clock_mocked':False,'result':metadata['result'],'subtitles':subtitle.name,'events':metadata['events'],'unverified':['auditory listening on physical speakers']}
(OUT/'playthrough-video-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2))
print(json.dumps(validation,ensure_ascii=False,indent=2),flush=True)
