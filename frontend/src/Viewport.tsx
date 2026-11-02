import { Component, Suspense, useEffect, useMemo, type ReactNode } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { Html, Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { Model, Part } from './types';

export type Display = 'assembly'|'body'|'front'|'exploded'|'transparent'|'section'|'layout'|'led';
export type CameraView = 'iso'|'top'|'front'|'back'|'side';

class CanvasBoundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed ? <div className="canvas-fallback"><strong>Podgląd WebGL jest niedostępny</strong><p>Użyj edytora 2D. Generowanie modeli i eksport nadal działają.</p></div> : this.props.children;}
}

function MeshPart({part,display,offset,selected,onSelect,lit,clip}:{part:Part;display:Display;offset:[number,number,number];selected:boolean;onSelect:(id:string)=>void;lit:boolean;clip:THREE.Plane[]}){
  const geometry=useMemo(()=>{
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(part.vertices.flat(),3));
    g.setIndex(part.faces.flat());g.computeVertexNormals();return g;
  },[part]);
  useEffect(()=>()=>geometry.dispose(),[geometry]);
  const reference=!part.printable;
  return <mesh geometry={geometry} position={offset} castShadow receiveShadow onClick={e=>{e.stopPropagation();onSelect(part.id);}}>
    <meshStandardMaterial color={selected ? new THREE.Color(part.color).lerp(new THREE.Color('#d9954c'),.22) : part.color}
      roughness={reference?.4:.48} metalness={reference?.22:.08}
      transparent={display==='transparent'&&part.kind==='body'||reference}
      opacity={display==='transparent'&&part.kind==='body'?.22:reference?.8:1}
      emissive={lit&&(part.kind==='diffuser'||reference)?'#ffc878':'#000000'} emissiveIntensity={lit?.65:0}
      side={THREE.DoubleSide} clippingPlanes={display==='section'?clip:[]} clipShadows />
  </mesh>;
}

function Rig({frame,view,display,reset}:{frame:[number,number,number];view:CameraView;display:Display;reset:number}){
  const {camera,size}=useThree();
  const key=frame.map(v=>Math.round(v)).join(',');
  useEffect(()=>{
    const [w,h,d]=frame;
    const distance=Math.max(w/(size.width/size.height),h,d*2,70)*2.2;
    const positions:Record<CameraView,[number,number,number]>={iso:[distance*.36,-distance*.35,distance*1.05],top:[0,0,distance*1.25],front:[0,-distance,d+10],back:[0,0,-distance],side:[distance,0,d+10]};
    camera.up.set(0,1,0);
    camera.position.set(...positions[view]);camera.lookAt(0,0,d/2);camera.near=.1;camera.far=20000;camera.updateProjectionMatrix();
  // Dimensions determine framing; material edits do not reset a user's orbit.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[key,view,display,reset,size.width,size.height]);
  return <OrbitControls makeDefault target={[0,0,frame[2]/2]} enableDamping minDistance={10} maxDistance={10000}/>;
}

function Scene({model,display,view,lit,dimensions,selected,onSelect,reset,dark}:{model:Model;display:Display;view:CameraView;lit:boolean;dimensions:boolean;selected:string|null;onSelect:(id:string)=>void;reset:number;dark:boolean}){
  const [w,h]=model.stats.dimensions;
  const b=model.stats.bounds;
  const cx=(b[0][0]+b[1][0])/2,cy=(b[0][1]+b[1][1])/2;
  const clip=useMemo(()=>[new THREE.Plane(new THREE.Vector3(0,-1,0),0)], []);
  const grid=useMemo(()=>{
    const span=Math.ceil(Math.max(w,h,200)/10)*20;
    const positions:number[]=[];
    for(let x=-span;x<=span;x+=10)positions.push(-span,x,0,span,x,0,x,-span,0,x,span,0);
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));return geometry;
  },[w,h]);
  useEffect(()=>()=>grid.dispose(),[grid]);
  let cursor=0,rowY=0,rowHeight=0;
  const offsets=new Map<string,[number,number,number]>();
  for(const p of model.parts){
    let offset:[number,number,number]=[-cx,-cy,0];
    if(display==='exploded'&&p.kind==='diffuser')offset=[-cx,-cy,Math.max(35,model.project.depth*1.6)];
    if(display==='layout'&&p.printable){
      const pw=p.bounds[1][0]-p.bounds[0][0],ph=p.bounds[1][1]-p.bounds[0][1];
      if(cursor+pw>Math.max(w,model.project.printer[0])*1.1&&cursor>0){cursor=0;rowY+=rowHeight+8;rowHeight=0;}
      offset=[cursor-p.bounds[0][0]-cx,rowY-p.bounds[0][1]-cy,-p.bounds[0][2]];cursor+=pw+8;rowHeight=Math.max(rowHeight,ph);
    }
    offsets.set(p.id,offset);
  }
  const visible=model.parts.filter(p=>display==='body'?p.kind==='body'||p.kind==='solid'||p.kind==='joiner':display==='front'?p.kind==='diffuser':display==='layout'?p.printable:display==='led'?p.kind!=='diffuser':true);
  const frame:[number,number,number]=[w,h,model.stats.dimensions[2]+(display==='exploded'?Math.max(35,model.project.depth*1.6):0)];
  if(display==='layout'&&visible.length){
    const bounds=new THREE.Box3();
    for(const p of visible){const off=offsets.get(p.id)!;for(const b of p.bounds)bounds.expandByPoint(new THREE.Vector3(b[0]+off[0],b[1]+off[1],b[2]+off[2]));}
    const center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());
    for(const [id,off] of offsets)offsets.set(id,[off[0]-center.x,off[1]-center.y,off[2]]);
    frame.splice(0,3,size.x,size.y,size.z);
  }
  return <>
    <color attach="background" args={[dark?'#202e30':'#edf0eb']}/>
    <ambientLight intensity={dark?1.2:1.6}/><directionalLight position={[100,-150,300]} intensity={3.2}/><directionalLight position={[-180,100,100]} intensity={1.8} color="#fff3d4"/>
    <lineSegments geometry={grid} position={[0,0,-model.project.base_thickness-.2]}><lineBasicMaterial color={dark?'#536b60':'#b4c0b3'} transparent opacity={.55} depthWrite={false}/></lineSegments>
    {visible.map(p=><MeshPart key={p.id} part={p} display={display} offset={offsets.get(p.id)!} selected={p.id===selected} onSelect={onSelect} lit={lit} clip={clip}/>)}
    {dimensions&&display!=='layout'&&<>
      <Line points={[[-w/2,-h/2-12,0],[w/2,-h/2-12,0]]} color="#83938a" lineWidth={1} dashed dashSize={2} gapSize={1}/>
      <Html center position={[0,-h/2-12,0]}><span className="measure">{w.toFixed(1)} mm</span></Html>
      <Line points={[[-w/2-12,-h/2,0],[-w/2-12,h/2,0]]} color="#83938a" lineWidth={1} dashed dashSize={2} gapSize={1}/>
      <Html center position={[-w/2-12,0,0]}><span className="measure">{h.toFixed(1)} mm</span></Html>
    </>}
    <Rig frame={frame} view={view} display={display} reset={reset}/>
  </>;
}

export default function Viewport(props:{model:Model;display:Display;view:CameraView;lit:boolean;dimensions:boolean;selected:string|null;onSelect:(id:string)=>void;reset:number;dark:boolean}){
  return <CanvasBoundary><Canvas dpr={[1,2]} gl={{antialias:true,preserveDrawingBuffer:true,localClippingEnabled:true}} camera={{position:[120,-120,300],fov:40,near:.1,far:20000}}>
    <Suspense fallback={null}><Scene {...props}/></Suspense>
  </Canvas></CanvasBoundary>;
}
