import { useRef, useState } from 'react';
import type { GeoJSON, Model, NeonPath, Placement, Project } from './types';

export function geometryPath(g:GeoJSON):string{
  const polygons=(g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[]) as number[][][][];
  return polygons.map(p=>p.map(r=>r.map(([x,y],i)=>`${i?'L':'M'}${x},${y}`).join(' ')+'Z').join(' ')).join(' ');
}
export default function Editor2D({model,project,onPlacements,onPaths,selected,setSelected,drawing,onDraw}:{model:Model;project:Project;onPlacements:(p:Placement[])=>void;onPaths:(p:NeonPath[])=>void;selected:string|null;setSelected:(id:string)=>void;drawing:boolean;onDraw:(point:[number,number])=>void}){
  const svg=useRef<SVGSVGElement>(null);
  const [drag,setDrag]=useState<{id:string;node?:number;dx:number;dy:number}|null>(null);
  const [draft,setDraft]=useState<{placements:Placement[];paths:NeonPath[]}|null>(null);
  const draftRef=useRef(draft);draftRef.current=draft;
  const [w,h]=model.stats.dimensions;
  const b=model.stats.bounds;
  const minX=b[0][0],maxY=b[1][1];
  const placements=draft?.placements||project.led.placements;
  const paths=draft?.paths||project.led.neon_paths;
  const coord=(e:React.PointerEvent):[number,number]=>{
    const p=svg.current!.createSVGPoint();p.x=e.clientX;p.y=e.clientY;
    const at=p.matrixTransform(svg.current!.getScreenCTM()!.inverse());return [at.x,-at.y];
  };
  const start=(e:React.PointerEvent,id:string,node?:number)=>{
    if(drawing)return;
    e.stopPropagation();const [x,y]=coord(e);setSelected(id);
    const p=node===undefined?project.led.placements.find(p=>p.id===id):null;
    setDrag({id,node,dx:p?p.x-x:0,dy:p?p.y-y:0});
    setDraft({placements:project.led.placements,paths:project.led.neon_paths});svg.current!.setPointerCapture(e.pointerId);
  };
  return <div className={`editor2d ${drawing?'drawing':''}`}><svg ref={svg} viewBox={`${minX-15} ${-maxY-15} ${w+30} ${h+30}`} role="img" aria-label="Edytor wnętrza litery w milimetrach"
    onPointerDown={e=>{if(drawing)onDraw(coord(e));}}
    onPointerMove={e=>{
      if(!drag)return;const [x,y]=coord(e);
      if(drag.node===undefined)setDraft({placements:project.led.placements.map(p=>p.id===drag.id?{...p,x:Math.round((x+drag.dx)*10)/10,y:Math.round((y+drag.dy)*10)/10}:p),paths:project.led.neon_paths});
      else setDraft({placements:project.led.placements,paths:project.led.neon_paths.map(p=>p.id===drag.id?{...p,points:p.points.map((q,i)=>i===drag.node?[Math.round(x*10)/10,Math.round(y*10)/10]:q)}:p)});
    }}
    onPointerUp={()=>{const current=draftRef.current;if(drag&&current){if(drag.node===undefined)onPlacements(current.placements);else onPaths(current.paths);}setDrag(null);setDraft(null);}}
    onPointerCancel={()=>{setDrag(null);setDraft(null);}}>
      <defs><pattern id="mm-grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="var(--grid)" strokeWidth=".25"/></pattern></defs>
      <rect x={minX-15} y={-maxY-15} width={w+30} height={h+30} fill="url(#mm-grid)"/>
      <g transform="scale(1 -1)">
        {model.outlines.map(o=><path key={o.id} d={geometryPath(o.geometry)} fill="var(--outline)" stroke="var(--muted)" strokeWidth=".35" fillRule="evenodd"/>)}
        <path d={geometryPath(model.cavity)} fill="var(--cavity)" stroke="var(--accent)" strokeWidth=".3" strokeDasharray="1 1" fillRule="evenodd"/>
        {paths.map(p=><g key={p.id}>
          <polyline points={p.points.map(q=>q.join(',')).join(' ')} fill="none" stroke={selected===p.id?'#db7e35':'#38a3a0'} strokeWidth={project.led.width+project.led.clearance*2} strokeLinecap="round" strokeLinejoin="round" opacity=".48"/>
          <polyline points={p.points.map(q=>q.join(',')).join(' ')} fill="none" stroke="#b9682d" strokeWidth=".5"/>
          {p.points.map(([x,y],i)=><circle key={i} cx={x} cy={y} r={selected===p.id?1.4:.8} fill="#fffaf2" stroke="#b9682d" strokeWidth=".4" onPointerDown={e=>start(e,p.id,i)}/>)}
        </g>)}
        {placements.map(p=>{
          const invalid=model.issues.some(i=>i.severity==='error'&&i.element_id===p.id);
          return <g key={p.id} transform={`translate(${p.x},${p.y}) rotate(${p.angle})`} className="placement" onPointerDown={e=>start(e,p.id)}>
            {['wire','screw','keyhole','magnet','standoff'].includes(p.kind)?<>
              <circle r={p.diameter/2} fill={invalid?'#df7666':'#f7f2e7'} stroke={selected===p.id?'#d07a35':'#597b77'} strokeWidth=".7"/>
              <path d="M-1 0H1M0 -1V1" stroke="#52746e" strokeWidth=".4"/>
              {p.kind==='keyhole'&&<rect x={-p.diameter/4} width={p.diameter/2} height={p.diameter*1.5} fill="#f7f2e7" stroke="#597b77" strokeWidth=".4"/>}
            </>:<>
              <rect x={-p.length/2-1} y={-p.width/2-1} width={p.length+2} height={p.width+2} rx=".4" fill={invalid?'#e4a19a':'#b5cec5'} stroke={selected===p.id?'#ce752e':'#527b70'} strokeWidth=".6"/>
              <rect x={-p.length/2} y={-p.width/2} width={p.length} height={p.width} rx=".2" fill={invalid?'#d27364':'#e6bd6c'} stroke="none"/>
              {['strip','pcb'].includes(p.kind)&&Array.from({length:Math.min(20,Math.max(1,Math.floor(p.length/6)))},(_,i)=><rect key={i} x={-p.length/2+2+i*6} y="-1.1" width="2.2" height="2.2" rx=".2" fill="#fff2be"/>)}
            </>}
          </g>;
        })}
      </g>
    </svg><div className="editor-caption"><span><i/> Obrys komory</span><span><i className="amber"/> LED / rowek</span><span>Siatka 10 mm · przeciągnij element lub węzeł</span></div></div>;
}
