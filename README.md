# CloudConvert
A mischievous attempt for convert file with together
## Purpose of development
TwitchRecorder가 만들어 내는 결과물은 기본적으로 스트리밍에 최적화 되어있는 인코딩 상태였기 때문에, 대부분 한번 인코딩을 거치면 용량이 많이 줄어들 수 있는 상태였습니다(저챗이 많음).

하지만 3900X만 대리고 변환 작업을 하기에는 작업의 양이 너무 많았습니다. 물론 안되는건 아니였지만, 3~4일 밀리는 날엔 컴퓨터를 끌 수 조차 없었습니다.

그래서 생각을 해보다가, 요즘 휴대폰의 성능이 나름 괜찮다는걸 기억해내서, 이 휴대폰들과 함께 변환작업을 하면 어떨까 하는 생각해서 뻘짓을 해봤습니다.
## Progress and Result of development

Host: AMD Ryzen 3900x at 4.13Ghz with (3200Mhz Overclocked Ram) + RX 570 (4GB Ram)

Node: Odroid N2+(4GB), Odroid-XU4, Samsung Galaxy S20, LG V50, Redmi K30 5G

Source Video : 2910MB(02:04:49) -> from TwitchRecorder, Just Chatting, small changes in movie

first attempt:
- ffmpeg: -preset veryfast, libx264, aac
- no preload
- mobile device is screen off without wakelock (!)
	- 712MB, 849 seconds - ffmpeg (no)
	- 691MB, 1266 seconds - cloudConvert, self node only (sn) (1.49x slower)
	- 695MB, 2417 seconds - cloudConvert, arm devices(S20, V50, K30 5G, N2, XU4) (arm) (2.84x slower)
	- 692MB, 1215 seconds - cloudConvert, self node with arm devices (full) (1.43x slower???)

I thought that loading the data right when I had to pass the job was the reason the job was so slow, so I had to preload the data from another thread.

second attempt:
- ffmpeg: -preset veryfast, libx264, aac
- preload (20 minutes)
- mobile device is screen on with screensaver (?)
	- 712MB, 849 seconds - ffmpeg (no)
	- 691MB, 966 seconds - cloudConvert, self node only (sn) (1.13x slower)
	- 694MB, 1481 seconds - cloudConvert, arm devices(S20, V50, K30 5G, N2, XU4) (arm) (1.74x slower)
	- 692MB, 670 seconds - cloudConvert, self node with arm devices (full) (1.26x faster)

I need more faster convert, so I tested some options
- preload -preset veryfast, libx264, aac, -x264opts opencl
	- 713MB, 1326 seconds - ffmpeg (no), - where my slight speed boost?
- cloudConvert, 'two' self node only (tsn)
	- 691MB, 575 seconds (1.47x faster) - I think ffmpeg didn't use cpu fully for short video or single video?

Finally...
- ffmpeg: preset veryfast, libx264, aac 
- after preload (20 minutes)
- dual-request when work not left
- screen off with cpu wakelock
	- 692MB, 539 seconds - cloudConvert, two self node with arm devices (full) (1.57x faster)




## Typical checklist
 - 그냥 실험용으로 만든 프로젝트이기에, 다른 영상에 적용하는경우 예상치 못한 행동을 보일 수 있습니다.
 - ffmpeg의 옵션등이 mp4(h264, aac)를 인코딩 하도록 조정되어 있습니다. 필요하다면 조정해야 합니다.
