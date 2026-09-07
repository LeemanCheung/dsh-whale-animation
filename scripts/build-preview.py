"""A white-backed, correctly timed 20fps review GIF; runtime WebPs remain60fps."""
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
states=['scout','surge','flow','breathe']
loops={}
for state in states:
    source=Image.open(ROOT/'assets'/f'whale-{state}.webp')
    samples=[];clock=0
    for frame in range(source.n_frames):
        source.seek(frame)
        rgba=source.convert('RGBA')
        clock+=source.info.get('duration',0)
        samples.append((clock,rgba.resize((144,144),Image.Resampling.LANCZOS)))
    loops[state]=(clock,samples)
frames=[]
for tick in range(0,36000,50):
    board=Image.new('RGB',(320,358),'#f6f8fa')
    draw=ImageDraw.Draw(board)
    for i,state in enumerate(states):
        duration,samples=loops[state]
        pose=next(pose for end,pose in samples if end>tick%duration)
        x=8+(i%2)*160;y=24+(i//2)*176
        board.paste(pose,(x,y),pose)
        draw.text((x+8,y-17),state.upper(),fill='#233142')
    frames.append(board)
target=ROOT/'docs/four-actions/preview.gif'
frames[0].save(target,save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=True,disposal=2)
print(f'Built {target.name}: {target.stat().st_size} bytes;36s common loop;20fps review only')
