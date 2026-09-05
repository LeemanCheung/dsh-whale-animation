/* NOCTURNE — an interactive, procedural sculpture.
 * Three.js is the preferred renderer. The identical GLSL runs through a small,
 * explicit WebGL adapter while the module is loading or when offline.
 * No external models, textures, fonts, audio files, analytics or API keys.
 */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const damp = (a, b, lambda, dt) => a + (b - a) * (1 - Math.exp(-lambda * dt));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const coarse = matchMedia('(pointer: coarse)');
  const host = $('#renderHost');
  const mobileQuery = matchMedia('(max-width:767px), (pointer:coarse) and (orientation:portrait) and (max-width:1023px), (pointer:coarse) and (max-height:600px)');
  let stageRect = host.getBoundingClientRect();
  let lastMobileFrame = 0;
  const works = [
    { title: '夜曲', latin: 'LIGATURE', masthead: 'NOCTURNE', description: '一根闭合的线。<br>镀铬曲面，缓慢回旋。' },
    { title: '回环', latin: 'APERTURE', masthead: 'APERTURE', description: '圆环错开半寸。<br>光，从缝隙里经过。' },
    { title: '余尘', latin: 'AFTERIMAGE', masthead: 'AFTERGLOW', description: '曲面散成薄片。<br>最后一点光，留在边缘。' }
  ];

  // One material, three signed distance fields. Lighting is an analytical
  // studio environment, reflected in the surface; it is not a painted image.
  const vertexShader = `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }
  `;
  const fragmentShader = `
    precision highp float;
    varying vec2 vUv;
    uniform vec2 uResolution;
    uniform vec2 uRotation;
    uniform vec2 uPointer;
    uniform float uTime;
    uniform float uMorph;
    uniform float uHold;
    uniform float uIntro;
    uniform float uFocus;
    uniform float uSeed;
    uniform float uMobile;
    #define PI 3.14159265359

    mat2 rotate2(float a) { float s=sin(a), c=cos(a); return mat2(c,-s,s,c); }
    float hash31(vec3 p) {
      p=fract(p*0.1031); p+=dot(p,p.yzx+33.33);
      return fract((p.x+p.y)*p.z);
    }
    float noise3(vec3 p) {
      vec3 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
      return mix(mix(mix(hash31(i),hash31(i+vec3(1,0,0)),f.x),
        mix(hash31(i+vec3(0,1,0)),hash31(i+vec3(1,1,0)),f.x),f.y),
        mix(mix(hash31(i+vec3(0,0,1)),hash31(i+vec3(1,0,1)),f.x),
        mix(hash31(i+vec3(0,1,1)),hash31(i+vec3(1,1,1)),f.x),f.y),f.z);
    }
    float sdTorus(vec3 p, vec2 t) { return length(vec2(length(p.xy)-t.x,p.z))-t.y; }
    vec3 localPosition(vec3 p) {
      p.xz = rotate2(-0.28 + uRotation.x + uTime*0.095 + uPointer.x*0.065)*p.xz;
      p.yz = rotate2(0.65 + uRotation.y + uPointer.y*0.055)*p.yz;
      p.xy = rotate2(-0.48 + 0.10*sin(uTime*0.14))*p.xy;
      return p;
    }
    float ligature(vec3 p) {
      float a=atan(p.y,p.x);
      vec2 q=vec2(length(p.xy)-1.06,p.z);
      vec2 c=0.49*vec2(cos(1.5*a),sin(1.5*a));
      float tube=0.292 + .018*sin(a*3.0+uTime*.35);
      return min(length(q-c),length(q+c))-tube;
    }
    float aperture(vec3 p) {
      vec3 q=p;
      q.xz=rotate2(0.3+sin(uTime*.18)*.13)*q.xz;
      float a=sdTorus(q,vec2(1.53,.12));
      q=p; q.yz=rotate2(.87+sin(uTime*.17)*.28)*q.yz;
      float b=sdTorus(q,vec2(1.18,.135));
      q=p; q.xz=rotate2(-.98+cos(uTime*.16)*.24)*q.xz;
      float c=sdTorus(q,vec2(.84,.145));
      q=p; q.yz=rotate2(1.35+sin(uTime*.21)*.22)*q.yz;
      float d=sdTorus(q,vec2(.47,.115));
      return min(min(a,b),min(c,d));
    }
    float afterimage(vec3 p) {
      p.xz=rotate2(p.y*.32 + .25*sin(uTime*.1))*p.xz;
      float nearest=floor(p.y/.165+.5);
      float distance=100.;
      // Consider neighbouring slices as well: a nearest-height-only lookup
      // overestimates distance near the poles and can skip thin surfaces.
      for(int i=-1;i<=1;i++) {
        float yy=clamp(nearest+float(i),-8.,8.)*.165;
        float rr=sqrt(max(.08,2.08-yy*yy));
        float phase=yy*3.0+uTime*.13;
        vec2 center=.12*vec2(sin(phase),cos(phase));
        float d=length(vec2(length(p.xz-center)-rr,p.y-yy))-.048;
        float ang=atan(p.z,p.x);
        float cut=sin(ang+yy*2.8+uTime*.1);
        d=max(d,(cut-.84)*.1);
        distance=min(distance,d);
      }
      return distance;
    }
    float mapScene(vec3 pos) {
      vec3 p=localPosition(pos);
      p/=1.0+.10*uHold;
      float d;
      if(uMorph<.001) d=ligature(p);
      else if(uMorph<.999) d=mix(ligature(p),aperture(p),smoothstep(0.,1.,uMorph));
      else if(uMorph<1.001) d=aperture(p);
      else if(uMorph<1.999) d=mix(aperture(p),afterimage(p),smoothstep(0.,1.,uMorph-1.));
      else d=afterimage(p);
      if(uHold>.005) {
        float grain=noise3(p*11.0+uSeed);
        d=max(d,(uHold*.84-grain)*.17);
      }
      return d*.44;
    }
    vec3 normalAt(vec3 p) {
      vec2 e=vec2(.0012,-.0012);
      return normalize(e.xyy*mapScene(p+e.xyy)+e.yyx*mapScene(p+e.yyx)+e.yxy*mapScene(p+e.yxy)+e.xxx*mapScene(p+e.xxx));
    }
    float softBox(vec2 p,vec2 b,float blur) {
      vec2 q=abs(p)-b;
      float d=length(max(q,0.))+min(max(q.x,q.y),0.);
      return 1.-smoothstep(-blur,blur,d);
    }
    vec3 studio(vec3 r) {
      vec2 a=vec2(atan(r.z,r.x),asin(clamp(r.y,-1.,1.)));
      vec3 color=vec3(.017,.020,.024);
      color+=vec3(.12,.135,.16)*smoothstep(-.7,.9,r.y);
      // Long rectangular softboxes, with a warm strip behind the object.
      float key=softBox(a-vec2(1.65,.48),vec2(.24,.76),.12);
      float fill=softBox(a-vec2(-.95,.7),vec2(.8,.12),.075);
      float edge=softBox(a-vec2(.16,-.02),vec2(.095,1.05),.06);
      float lower=softBox(a-vec2(2.4,-.65),vec2(.62,.045),.05);
      float white=softBox(a-vec2(-2.6,.1),vec2(.19,.65),.085);
      color+=key*vec3(3.0,3.15,3.4);
      color+=fill*vec3(2.1,2.25,2.50);
      color+=edge*vec3(3.2,.30,.105);
      color+=lower*vec3(1.5,.72,.35);
      color+=white*vec3(1.3,1.42,1.6);
      return color;
    }
    vec3 aces(vec3 x) { return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.); }
    void main() {
      float aspect=uResolution.x/uResolution.y;
      vec2 q=(gl_FragCoord.xy-.5*uResolution)/uResolution.y;
      float mobile=uMobile;
      q.x-=mix(aspect*.176,0.,mobile)*(1.-uFocus);
      q.y+=mix(.035,0.,mobile)*(1.-uFocus);
      float lens=mix(3.66*max(1.,1.12/aspect),3.12*max(1.,1.0/aspect),mobile);
      lens*=mix(1.,.90,uFocus);
      vec3 ro=vec3(0.,0.,6.6);
      vec3 rd=normalize(vec3(q*lens,-4.15));
      // Bound the expensive field evaluation to a sphere.
      float b=dot(ro,rd), c=dot(ro,ro)-5.29;
      float h=b*b-c;
      if(h<0.) { gl_FragColor=vec4(0.); return; }
      float t=max(0.,-b-sqrt(h));
      float farT=-b+sqrt(h);
      float closest=2.;
      float dist=1.;
      bool hit=false;
      for(int i=0;i<156;i++) {
        vec3 p=ro+rd*t;
        dist=mapScene(p);
        closest=min(closest,dist);
        if(dist<.00125){hit=true;break;}
        t+=max(dist,.00085);
        if(t>farT)break;
      }
      if(!hit){gl_FragColor=vec4(0.);return;}
      vec3 p=ro+rd*t;
      vec3 n=normalAt(p);
      vec3 lp=localPosition(p);
      // Subtle machining marks, intentionally too fine to read as a texture.
      float brush=sin(lp.y*125.+lp.x*35.)*.0015;
      n=normalize(n+vec3(brush,brush*.35,-brush*.5));
      vec3 reflection=reflect(rd,n);
      float facing=max(dot(n,-rd),0.);
      float fresnel=pow(1.-facing,5.);
      float ao=clamp(1.-(.17-mapScene(p+n*.17))*1.8-(.48-mapScene(p+n*.48))*.60,.32,1.);
      vec3 color=studio(reflection)*mix(vec3(.73,.78,.85),vec3(.97),fresnel)*ao;
      color+=vec3(.014,.016,.019)*(0.4+0.6*max(n.y,0.));
      float rim=pow(1.-facing,3.0)*smoothstep(-.4,1.,n.x);
      color+=vec3(.52,.055,.016)*rim*.75;
      float cutGlow=uHold*pow(1.-facing,2.0);
      color+=vec3(.5,.065,.017)*cutGlow*.22;
      color=pow(aces(color),vec3(1./2.2));
      // A frame-stable subpixel dither prevents banding in the dark gradients.
      color+=(hash31(vec3(gl_FragCoord.xy,17.))-.5)/255.;
      gl_FragColor=vec4(color,uIntro);
    }
  `;

  const state = {
    width: innerWidth, height: innerHeight, ratio: Math.min(devicePixelRatio || 1, 1.25, Math.sqrt(1600000/(innerWidth*innerHeight))),
    time: 3.2, elapsed: 0, morph: 0, targetMorph: 0, chapter: 0,
    hold: 0, holdTarget: 0, rotation: [0,0], targetRotation: [0,0],
    pointer: [0,0], targetPointer: [0,0], intro: 0,
    focused: false, focus: 0, paused: reduced.matches, sound: false,
    seed: 7.23, dragging: false, reduced: reduced.matches,
    rendererName: 'WebGL · 本地', alive: true, frames: 0
  };
  if (new URLSearchParams(location.search).get('quality') === 'low') state.ratio=.6;
  let renderer, raf=0, lastTime=performance.now(), lastReadout=0, resizeTimer;
  let changeToken=0, toastTimer=0, down=null, holdTimer=null, frameAverage=16.7;
  let hiddenByDialog=false;
  const startTime=performance.now();
  let lastSignature='';
  const materialUniforms=()=>({
    uResolution: [Math.round(state.width*state.ratio),Math.round(state.height*state.ratio)],
    uRotation: state.rotation, uPointer: state.pointer, uTime:state.time,
    uMorph:state.morph, uHold:state.hold, uIntro:state.intro,
    uFocus:state.focus, uSeed:state.seed, uMobile:mobileQuery.matches?1:0
  });

  function nativeRenderer() {
    const canvas=document.createElement('canvas');
    canvas.setAttribute('aria-hidden','true');
    const gl=canvas.getContext('webgl',{alpha:true,antialias:false,premultipliedAlpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
    if(!gl)throw new Error('WebGL 不可用，请开启浏览器的硬件加速。');
    function compile(type,source){
      const shader=gl.createShader(type); gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)){
        const log=gl.getShaderInfoLog(shader);gl.deleteShader(shader);throw new Error(log);
      }return shader;
    }
    const vertex=compile(gl.VERTEX_SHADER,'precision highp float;\nattribute vec3 position;\nattribute vec2 uv;\n'+vertexShader);
    const fragment=compile(gl.FRAGMENT_SHADER,fragmentShader);
    const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.deleteShader(vertex);gl.deleteShader(fragment);gl.useProgram(program);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,0,0,1,-1,1,0,-1,1,0,1,-1,1,0,1,1,-1,1,0,1,1,1,1]),gl.STATIC_DRAW);
    const pos=gl.getAttribLocation(program,'position');
    gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,16,0);
    const uv=gl.getAttribLocation(program,'uv');
    if(uv!==-1){gl.enableVertexAttribArray(uv);gl.vertexAttribPointer(uv,2,gl.FLOAT,false,16,8);}
    const uniforms={};Object.keys(materialUniforms()).forEach(k=>uniforms[k]=gl.getUniformLocation(program,k));
    let lost=false,disposed=false;
    canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();if(disposed)return;lost=true;notify('画面已暂停：图形上下文中断。');});
    canvas.addEventListener('webglcontextrestored',()=>location.reload());
    return {
      canvas, name:'WebGL · 本地',
      resize(w,h,r){canvas.width=Math.max(1,Math.round(w*r));canvas.height=Math.max(1,Math.round(h*r));gl.viewport(0,0,canvas.width,canvas.height);},
      render(){if(lost)return;gl.useProgram(program);const u=materialUniforms();for(const k in u){if(Array.isArray(u[k]))gl.uniform2f(uniforms[k],u[k][0],u[k][1]);else gl.uniform1f(uniforms[k],u[k]);}gl.drawArrays(gl.TRIANGLES,0,6);},
      dispose(){disposed=true;gl.deleteBuffer(buffer);gl.deleteProgram(program);gl.getExtension('WEBGL_lose_context')?.loseContext();canvas.remove();}
    };
  }

  function threeRenderer(THREE) {
    const canvas=document.createElement('canvas');canvas.setAttribute('aria-hidden','true');
    const engine=new THREE.WebGLRenderer({canvas,alpha:true,antialias:false,premultipliedAlpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
    engine.setClearColor(0x000000,0);
    engine.toneMapping=THREE.NoToneMapping;
    const scene=new THREE.Scene();
    const camera=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
    const uniforms={};
    const initial=materialUniforms();
    Object.keys(initial).forEach(k=>uniforms[k]={value:Array.isArray(initial[k])?new THREE.Vector2(...initial[k]):initial[k]});
    const material=new THREE.ShaderMaterial({uniforms,vertexShader,fragmentShader,transparent:true,blending:THREE.NoBlending,depthWrite:false,depthTest:false});
    const geometry=new THREE.PlaneGeometry(2,2);
    const plane=new THREE.Mesh(geometry,material);plane.frustumCulled=false;scene.add(plane);
    return {
      canvas,name:`Three.js r${THREE.REVISION}`,
      resize(w,h,r){engine.setPixelRatio(r);engine.setSize(w,h,false);},
      render(){const values=materialUniforms();for(const k in values){if(Array.isArray(values[k]))uniforms[k].value.set(...values[k]);else uniforms[k].value=values[k];}engine.render(scene,camera);},
      dispose(){geometry.dispose();material.dispose();engine.dispose();engine.forceContextLoss();canvas.remove();}
    };
  }

  function setRenderer(next){
    next.resize(state.width,state.height,state.ratio);
    next.render();
    const previous=renderer;
    renderer=next;
    host.replaceChildren(next.canvas);
    state.rendererName=next.name;
    $('#backendLabel').textContent=next.name;
    // Give the retired context a no-op loss handler before deliberate cleanup.
    if(previous)previous.dispose();
  }
  async function preferThree(){
    const sources=[
      './vendor/three.module.min.js',
      'https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.min.js',
      'https://esm.sh/three@0.180.0'
    ];
    for(const source of sources){
      try{
        // A remote failure never blocks the artwork.
        const THREE=await Promise.race([
          import(source),new Promise((_,reject)=>setTimeout(()=>reject(new Error('module timeout')),2500))
        ]);
        if(!state.alive)return;
        setRenderer(threeRenderer(THREE));
        return true;
      }catch(_){ /* Identical local shader keeps running. */ }
    }
  }

  function notify(message){$('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),3200);}
  function scrollProgress(){
    const first=$('#study-1').offsetTop;
    const last=$('#study-3').offsetTop;
    return clamp((scrollY-first)/Math.max(1,last-first),0,1);
  }
  function onScroll(){
    const progress=scrollProgress();
    state.targetMorph=progress*2;
    const c=Math.round(state.targetMorph);
    if(c!==state.chapter)changeCaption(c);
    $('#progressFill').style.width=`${(1+state.targetMorph)/3*100}%`;
  }
  function goToChapter(index){
    const c=((index%3)+3)%3;
    const element=$(`#study-${c+1}`);
    element.scrollIntoView({behavior:state.reduced?'instant':'smooth',block:'start'});
  }
  function changeCaption(index){
    state.chapter=index;
    $$('.chapter').forEach((el,i)=>{el.classList.toggle('active',i===index);el.setAttribute('aria-pressed',String(i===index));});
    const token=++changeToken;
    $('#fixedCaption').classList.add('changing');$('#masthead').classList.add('changing');
    setTimeout(()=>{
      if(token!==changeToken)return;
      const work=works[index];
      $('#workTitle').textContent=work.title;
      $('#workLabel').textContent=`00${index+1} — ${work.latin}`;
      $('#workDescription').innerHTML=work.description;
      $('#masthead').textContent=work.masthead;
      $('#masthead').dataset.long=String(work.masthead.length>8);
      $('#largeIndex').textContent=`00${index+1}`;
      $('#artOrdinal').textContent=`0${index+1}`;
      $('#nextLabel').textContent=index===2?'回到第一件':'下一件作品';
      $('#fixedCaption').classList.remove('changing');$('#masthead').classList.remove('changing');
    },state.reduced?0:220);
  }
  function setPaused(value){
    state.paused=value;
    $('#pauseBtn').setAttribute('aria-pressed',String(value));
    $('#pauseBtn').setAttribute('aria-label',value?'播放动画':'暂停动画');
    $('#pauseBtn').title=value?'播放 · 空格':'暂停 · 空格';
    $('#pauseIcon').setAttribute('d',value?'M6 3.5 13 9l-7 5.5Z':'M6 4v10M12 4v10');
    $('#pauseIcon').setAttribute('fill',value?'currentColor':'none');
    if(value)$('#timeReadout').textContent='PAUSED';
    updateAudio();
  }
  function setFocus(value){
    state.focused=value;document.body.classList.toggle('focus-mode',value);
    requestAnimationFrame(syncViewport);
    ['.site-header','.fixed-caption','.control-dock'].forEach(selector=>$(selector).inert=value);
    $('#focusBtn').setAttribute('aria-pressed',String(value));
    if(value)$('#leaveFocus').focus({preventScroll:true});
    else (coarse.matches?host:$('#focusBtn')).focus({preventScroll:true});
  }
  async function toggleFullscreen(){
    try{
      if(document.fullscreenElement)await document.exitFullscreen();
      else if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();
      else {setFocus(!state.focused);notify('此浏览器不支持全屏，已切换观赏模式。');}
    }catch(_){notify('此窗口不支持全屏。按 H 可进入无字观赏。');}
  }

  // Sound is synthesized only after an explicit click. It is never downloaded.
  let audio=null;
  function makeAudio(){
    const AudioContext=window.AudioContext||window.webkitAudioContext;
    if(!AudioContext)throw new Error('no audio');
    const context=new AudioContext();
    const master=context.createGain();master.gain.value=0;master.connect(context.destination);
    const filter=context.createBiquadFilter();filter.type='lowpass';filter.frequency.value=560;filter.Q.value=.45;filter.connect(master);
    const oscillators=[];
    [55,82.4069,110.13,164.82].forEach((frequency,i)=>{
      const osc=context.createOscillator();osc.type='sine';osc.frequency.value=frequency;
      const gain=context.createGain();gain.gain.value=[.13,.06,.035,.025][i];
      osc.connect(gain);gain.connect(filter);osc.start();oscillators.push(osc);
    });
    const lfo=context.createOscillator();lfo.frequency.value=.11;
    const lfoGain=context.createGain();lfoGain.gain.value=30;lfo.connect(lfoGain);lfoGain.connect(filter.frequency);lfo.start();
    return {context,master,filter,oscillators,lfo};
  }
  async function toggleSound(){
    try{
      audio ||= makeAudio();
      if(audio.context.state==='suspended')await audio.context.resume();
      state.sound=!state.sound;
      $('#soundBtn').setAttribute('aria-pressed',String(state.sound));
      $('#soundBtn').setAttribute('aria-label',state.sound?'关闭声音':'开启声音');
      $('#soundLabel').textContent=state.sound?'声音开启':'声音关闭';
      updateAudio();
    }catch(_){notify('声音未能开启，画面不受影响。');}
  }
  function updateAudio(){
    if(!audio)return;
    const audible=state.sound&&!document.hidden&&!hiddenByDialog;
    audio.master.gain.setTargetAtTime(audible?(state.paused?.26:.42):0,audio.context.currentTime,.5);
  }

  // Pointer state explicitly distinguishes a hold, a drag, and vertical touch
  // scrolling. A gesture interrupted by pointercancel can never leave a hold on.
  function releasePointer(){
    if(down?.id!=null){try{host.releasePointerCapture(down.id);}catch(_){}}
    clearTimeout(holdTimer);holdTimer=null;down=null;state.dragging=false;state.holdTarget=0;
    $('#cursor').classList.remove('active');$('#holdMeter').classList.remove('visible');
  }
  host.addEventListener('pointerdown',e=>{
    if(e.button!==0&&e.pointerType==='mouse')return;
    if(hiddenByDialog||!e.isPrimary){releasePointer();return;}
    releasePointer();
    down={x:e.clientX,y:e.clientY,id:e.pointerId,wasDrag:false,touch:e.pointerType!=='mouse'};
    state.dragging=true;
    try{host.setPointerCapture(e.pointerId);}catch(_){}
    holdTimer=setTimeout(()=>{
      if(!down||down.wasDrag)return;
      state.holdTarget=1;$('#cursor').classList.add('active');$('#holdMeter').classList.add('visible');
      if(down.touch&&navigator.vibrate)navigator.vibrate(12);
    },360);
  });
  window.addEventListener('pointermove',e=>{
    state.targetPointer=[(e.clientX/Math.max(1,innerWidth)-.5)*2,-(e.clientY/Math.max(1,innerHeight)-.5)*2];
    const cursor=$('#cursor');
    if(!coarse.matches){
      const interactive=e.target.closest?.('button,a,dialog,header,footer');
      cursor.style.opacity=interactive?'0':'.8';
      const half=cursor.classList.contains('active')?32.5:24;
      cursor.style.transform=`translate(${e.clientX-half}px,${e.clientY-half}px)`;
    }
    if(!down||e.pointerId!==down.id)return;
    const dx=e.clientX-down.x,dy=e.clientY-down.y;
    if(down.touch&&!down.wasDrag&&Math.abs(dy)>Math.abs(dx)*1.2&&Math.abs(dy)>7){releasePointer();return;}
    if(Math.abs(dx)+Math.abs(dy)>3){
      if(!down.wasDrag&&Math.abs(dx)+Math.abs(dy)<8)return;
      down.wasDrag=true;clearTimeout(holdTimer);
      state.targetRotation[0]+=dx*.006;
      state.targetRotation[1]=clamp(state.targetRotation[1]+dy*.005,-1.4,1.4);
      down.x=e.clientX;down.y=e.clientY;
    }
  },{passive:true});
  window.addEventListener('pointerup',releasePointer);
  window.addEventListener('pointercancel',releasePointer);
  host.addEventListener('lostpointercapture',releasePointer);
  host.addEventListener('touchstart',e=>{if(e.touches.length>1)releasePointer();},{passive:true});
  window.addEventListener('blur',releasePointer);
  document.documentElement.addEventListener('pointerleave',()=>$('#cursor').style.opacity='0');
  host.addEventListener('contextmenu',e=>e.preventDefault());
  host.addEventListener('dblclick',()=>{state.targetRotation=[0,0];notify('视角已归位。');});

  $$('.chapter').forEach(button=>button.addEventListener('click',()=>goToChapter(Number(button.dataset.chapter))));
  $('#nextBtn').addEventListener('click',()=>goToChapter(state.chapter+1));
  $('#pauseBtn').addEventListener('click',()=>setPaused(!state.paused));
  $('#focusBtn').addEventListener('click',()=>setFocus(!state.focused));
  $('#leaveFocus').addEventListener('click',()=>setFocus(false));
  $('#soundBtn').addEventListener('click',toggleSound);
  $('#fullscreenBtn').addEventListener('click',toggleFullscreen);
  document.addEventListener('fullscreenchange',()=>{
    $('#fullscreenBtn').setAttribute('aria-label',document.fullscreenElement?'退出全屏':'进入全屏');
  });
  const dialog=$('#notesDialog');
  let modalScroll=0;
  function openModal(target){modalScroll=scrollY;target.showModal();document.body.style.overflow='hidden';hiddenByDialog=true;releasePointer();updateAudio();}
  function closeModal(){document.body.style.overflow='';hiddenByDialog=false;updateAudio();requestAnimationFrame(syncViewport);}
  $('#notesBtn').addEventListener('click',()=>openModal(dialog));
  $('#closeNotes').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
  dialog.addEventListener('close',closeModal);
  let posterFile=null,posterUrl=null;
  $('#closeExport').addEventListener('click',()=>$('#exportDialog').close());
  $('#exportDialog').addEventListener('close',closeModal);
  $('#sharePoster').addEventListener('click',async()=>{if(!posterFile)return;try{await navigator.share({files:[posterFile],title:'NOCTURNE / 夜曲'});}catch(e){if(e.name!=='AbortError')notify('请长按图片保存。');}});
  window.addEventListener('keydown',e=>{
    if(e.altKey||e.metaKey||e.ctrlKey||e.target.matches('input,textarea,select'))return;
    if(dialog.open||$('#exportDialog').open)return;
    const onButton=e.target.closest?.('button,a');
    if(e.code==='Space'&&!onButton){e.preventDefault();setPaused(!state.paused);}
    else if(e.key.toLowerCase()==='h')setFocus(!state.focused);
    else if(e.key.toLowerCase()==='f')toggleFullscreen();
    else if(e.key==='Escape'&&state.focused)setFocus(false);
    else if(/^[123]$/.test(e.key))goToChapter(Number(e.key)-1);
    else if(e.key==='ArrowLeft'){e.preventDefault();state.targetRotation[0]-=.12;}
    else if(e.key==='ArrowRight'){e.preventDefault();state.targetRotation[0]+=.12;}
    else if(e.key==='ArrowUp'){e.preventDefault();state.targetRotation[1]=clamp(state.targetRotation[1]-.12,-1.4,1.4);}
    else if(e.key==='ArrowDown'){e.preventDefault();state.targetRotation[1]=clamp(state.targetRotation[1]+.12,-1.4,1.4);}
    else if(e.key.toLowerCase()==='d'&&!e.repeat){state.holdTarget=1;$('#holdMeter').classList.add('visible');}
  });
  window.addEventListener('keyup',e=>{if(e.key.toLowerCase()==='d')releasePointer();});
  window.addEventListener('scroll',onScroll,{passive:true});
  function fitStage(){
    // Only update backing stores here; never mutate the observed CSS box.
    stageRect=host.getBoundingClientRect();
    const w=Math.max(1,Math.round(stageRect.width)),h=Math.max(1,Math.round(stageRect.height));
    if(state.width!==w||state.height!==h){
      state.width=w;state.height=h;
      state.ratio=Math.min(devicePixelRatio||1,mobileQuery.matches?1.5:1.25,Math.sqrt(1300000/(w*h)));
      renderer?.resize(w,h,state.ratio);lastSignature='';resizeDust();
    }
  }
  function syncViewport(){
    const vv=window.visualViewport;
    const height=vv&&Math.abs(vv.scale-1)<.01?vv.height:innerHeight;
    const value=`${Math.round(height)}px`;
    if(document.documentElement.style.getPropertyValue('--view-height')!==value)
      document.documentElement.style.setProperty('--view-height',value);
    fitStage();onScroll();
  }
  function scheduleResize(){clearTimeout(resizeTimer);resizeTimer=setTimeout(syncViewport,50);}
  window.addEventListener('resize',scheduleResize,{passive:true});
  window.visualViewport?.addEventListener('resize',scheduleResize,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(syncViewport,180));
  mobileQuery.addEventListener('change',scheduleResize);
  document.addEventListener('visibilitychange',()=>{lastTime=performance.now();if(document.hidden)releasePointer();updateAudio();});
  reduced.addEventListener('change',e=>{state.reduced=e.matches;if(e.matches)setPaused(true);});

  const dustCanvas=$('#dustCanvas');const dust=dustCanvas.getContext('2d');
  const particles=Array.from({length:180},(_,i)=>{
    const t=i*2.3999632297;
    return {a:t,b:Math.sin(i*17.13)*1.8,z:Math.cos(i*37.31),r:.4+((i*17)%19)/19,phase:i*.723};
  });
  function resizeDust(){const r=Math.min(devicePixelRatio||1,1.5);dustCanvas.width=Math.max(1,Math.round(state.width*r));dustCanvas.height=Math.max(1,Math.round(state.height*r));}
  function drawDust(){
    const w=dustCanvas.width,h=dustCanvas.height;dust.clearRect(0,0,w,h);
    const mobile=mobileQuery.matches;
    const centerX=w*(mobile?.5:.676)+(w*.5-w*(mobile?.5:.676))*state.focus;
    const centerY=h*(mobile?.5:.535)+(h*.5-h*(mobile?.5:.535))*state.focus;
    const radius=Math.min(w*(mobile?.32:.25),h*.35);
    const hold=state.hold;
    const count=hold>.02?180:20;
    for(let i=0;i<count;i++){
      const p=particles[i];
      const a=p.a+state.time*(.025+(i%3)*.003);
      const spread=1.15+hold*(.5+(i%11)*.08);
      const x=centerX+Math.cos(a)*radius*spread*p.r;
      const y=centerY+Math.sin(a)*radius*.78*spread+Math.sin(state.time*.13+p.phase)*5;
      const alpha=(hold>.02?hold*.6:.16)*(0.4+.6*(p.z+1)*.5);
      const size=(hold>.02?(.6+hold*(i%3)*.35):.65)*Math.min(devicePixelRatio||1,1.5);
      dust.fillStyle=i%7===0?`rgba(239,87,59,${alpha})`:`rgba(200,209,215,${alpha})`;
      dust.fillRect(x,y,size,size);
    }
  }

  let exporting=false;
  async function saveFrame(){
    if(exporting||!renderer)return;
    exporting=true;$('#saveBtn').disabled=true;notify('正在留住这一帧。');
    const originalRatio=state.ratio;
    try{
      await new Promise(resolve=>setTimeout(resolve,50));
      const ratio=Math.min(2,Math.sqrt(3000000/(state.width*state.height)));
      state.ratio=ratio;renderer.resize(state.width,state.height,ratio);renderer.render();
      const image=new Image();image.src=renderer.canvas.toDataURL('image/png');await image.decode();
      const out=document.createElement('canvas');out.width=1080;out.height=1440;
      const ctx=out.getContext('2d');const w=out.width,h=out.height,m=w*.055;
      ctx.fillStyle='#0b0c0e';ctx.fillRect(0,0,w,h);
      const ambient=ctx.createRadialGradient(w*.65,h*.45,0,w*.65,h*.45,w*.6);ambient.addColorStop(0,'#232428');ambient.addColorStop(1,'#0b0c0e');ctx.fillStyle=ambient;ctx.fillRect(0,0,w,h);
      ctx.fillStyle='#deddd5';ctx.font=`${Math.round(w*.155)}px "Times New Roman",serif`;ctx.fillText(works[state.chapter].masthead,m,h*.25,w-m*2);
      const fit=Math.min(w*.98/image.width,h*.53/image.height);
      ctx.drawImage(image,(w-image.width*fit)/2,h*.27+(h*.53-image.height*fit)/2,image.width*fit,image.height*fit);
      ctx.fillStyle='#ef573b';ctx.fillRect(m,h*.105,20*ratio,ratio);
      ctx.fillStyle='#c1c1b8';ctx.font=`${Math.round(w*.009+3)}px monospace`;ctx.fillText(`NOCTURNE / FORM STUDY 00${state.chapter+1}`,m,h*.09);
      ctx.fillStyle='#edece4';ctx.font=`${Math.round(w*.044)}px "Songti SC",serif`;ctx.fillText(works[state.chapter].title,m,h*.82);
      ctx.fillStyle='#969a92';ctx.font=`${Math.round(w*.009+3)}px monospace`;ctx.fillText(works[state.chapter].latin,m,h*.855);
      ctx.strokeStyle='#55564c';ctx.lineWidth=.5*ratio;ctx.beginPath();ctx.moveTo(m,h*.9);ctx.lineTo(w-m,h*.9);ctx.stroke();
      ctx.fillText(`EDITION 00${state.chapter+1} / 003`,m,h*.935);
      const date=new Date().toLocaleDateString('en-CA');ctx.textAlign='right';ctx.fillText(date,w-m,h*.935);
      const blob=await new Promise(resolve=>out.toBlob(resolve,'image/png'));
      if(!blob)throw new Error('empty export');
      const url=URL.createObjectURL(blob);
      const filename=`NOCTURNE-${state.chapter+1}-${Date.now()}.png`;
      if(coarse.matches){
        if(posterUrl)URL.revokeObjectURL(posterUrl);
        posterUrl=url;posterFile=new File([blob],filename,{type:'image/png'});
        $('#exportImage').src=url;$('#downloadPoster').href=url;$('#downloadPoster').download=filename;
        $('#sharePoster').hidden=!(navigator.canShare&&navigator.canShare({files:[posterFile]}));
        openModal($('#exportDialog'));
        $('#toast').classList.remove('visible');
      }else{
        const link=document.createElement('a');link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
        setTimeout(()=>URL.revokeObjectURL(url),30000);notify('这一帧，留给你。');
      }
    }catch(error){console.error('Frame export:',error);notify('保存失败。可使用浏览器截图保留画面。');}
    finally{state.ratio=originalRatio;renderer.resize(state.width,state.height,state.ratio);exporting=false;$('#saveBtn').disabled=false;}
  }
  $('#saveBtn').addEventListener('click',saveFrame);

  function animate(now){
    raf=requestAnimationFrame(animate);
    if(mobileQuery.matches&&now-lastMobileFrame<31)return;
    lastMobileFrame=now;
    const frameMs=now-lastTime;lastTime=now;
    if(document.hidden||exporting||!renderer)return;
    const dt=clamp(frameMs/1000,0,.065);
    if(!state.paused&&!hiddenByDialog){state.time+=dt;state.elapsed+=dt;}
    state.intro=clamp((now-startTime)/1500,0,1);
    state.morph=damp(state.morph,state.targetMorph,state.reduced?100:5.5,dt);
    if(Math.abs(state.morph-state.targetMorph)<.001)state.morph=state.targetMorph;
    state.hold=damp(state.hold,state.holdTarget,3.5,dt);
    state.focus=damp(state.focus,state.focused?1:0,3.5,dt);
    for(let i=0;i<2;i++){
      state.rotation[i]=damp(state.rotation[i],state.targetRotation[i],8,dt);
      state.pointer[i]=damp(state.pointer[i],state.targetPointer[i],2.5,dt);
    }
    const signature=[state.time,state.morph,state.hold,state.focus,...state.rotation,...state.pointer,state.intro,state.ratio,state.width,state.height].map(v=>Math.round(v*10000)).join(',');
    const rendered=signature!==lastSignature;
    if(rendered){renderer.render();drawDust();lastSignature=signature;state.frames++;}
    $('#holdMeter>span').style.transform=`scaleX(${state.hold})`;
    if(audio&&state.sound){audio.filter.frequency.setTargetAtTime(560+state.hold*1700+state.morph*170,audio.context.currentTime,.2);}
    if(now-lastReadout>500){
      if(!state.paused)$('#timeReadout').textContent=`${String(Math.floor(state.elapsed/60)).padStart(2,'0')}:${String(Math.floor(state.elapsed%60)).padStart(2,'0')}`;
      const angle=v=>`${v>=0?'+':'−'}${String(Math.abs(Math.round(v*180/Math.PI))%360).padStart(3,'0')}°`;
      $('#rotationReadout').textContent=`X ${angle(state.rotation[0])}   Y ${angle(state.rotation[1])}`;
      lastReadout=now;
    }
    // Monotonic, bounded quality reduction; it never oscillates between modes.
    if(rendered&&!state.paused&&state.frames>12){
      frameAverage=frameAverage*.95+Math.min(frameMs,150)*.05;
      if(state.frames%45===0&&frameAverage>(mobileQuery.matches?48:30)&&state.ratio>(mobileQuery.matches?.9:.66)){
        state.ratio=Math.max(mobileQuery.matches?.85:.65,state.ratio-.15);renderer.resize(state.width,state.height,state.ratio);
      }
    }
  }
  async function start(){
    let fallbackTimer;
    const finish=()=>{
      $('#loadLine').classList.add('loaded');
      $('#renderLabel').textContent='实时演算';
    };
    const fallback=()=>{if(!renderer){setRenderer(nativeRenderer());finish();}};
    try{
      syncViewport();resizeDust();onScroll();setPaused(state.paused);
      state.morph=state.targetMorph;
      if(coarse.matches)$('#interactionHint').innerHTML='横拖旋转 <b>·</b> 长按解构 <b>·</b> 上滑换件';
      raf=requestAnimationFrame(animate);
      if(new URLSearchParams(location.search).get('renderer')==='native')fallback();
      else {
        fallbackTimer=setTimeout(()=>{try{fallback();}catch(_){}},700);
        await preferThree();
        clearTimeout(fallbackTimer);fallback();finish();
      }
    }catch(error){
      clearTimeout(fallbackTimer);
      console.error('NOCTURNE initialization:',error);
      const message=document.createElement('div');message.className='render-error';
      message.textContent='这台设备暂时无法绘制雕塑。请开启浏览器硬件加速，或换用支持 WebGL 的浏览器。';
      host.replaceChildren(message);$('#renderLabel').textContent='图形不可用';
    }
  }
  // Observe final CSS layout after WebKit viewport and media-query updates.
  // Defer GPU backing-store work until outside ResizeObserver delivery.
  const stageObserver=typeof ResizeObserver==="function"?new ResizeObserver(()=>{if(state.alive)requestAnimationFrame(fitStage);}):null;
  stageObserver?.observe(host);
  window.__NOCTURNE__={
    version:'1.1.0',state,goToChapter,setPaused,setFocus,
    get renderer(){return renderer;},vertexShader,fragmentShader,
    // Useful to host applications embedding this page in a route.
    dispose(){state.alive=false;stageObserver?.disconnect();cancelAnimationFrame(raf);renderer?.dispose();audio?.context.close();}
  };
  start();
})();
