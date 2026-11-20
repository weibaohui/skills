// Artifact Tool components. Geometry and fontSize are CSS px, 96 DPI.
// Pass an Artifact Tool slide; no runtime path is hardcoded in this module.
export const C = { blue:'#0070C0', tab:'#4472C4', border:'#517BAA', pale:'#E6F1F7', paleBlue:'#DDEBF7', cyan:'#00A9DC', orange:'#EF8626', red:'#E3292E', green:'#E2F0D9', yellow:'#FFF2CC', ink:'#151515', grey:'#A6A6A6' };
export const FONT = 'Microsoft YaHei';
export const pt = n => n * 96 / 72;
let seq = 0;
export function rect(slide,x,y,w,h,fill='none',stroke='none',sw=0,name='rect') {
  return slide.shapes.add({name:`${name}-${++seq}`, geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:sw,style:'solid'}});
}
export function txt(slide,text,x,y,w,h,size=11,color=C.ink,bold=false,align='left',extra={}) {
  const s=rect(slide,x,y,w,h,'none','none',0,'text'); s.text=text;
  s.text.style={fontSize:size,typeface:FONT,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0,lineSpacing:1.12,...extra};
  return s;
}
export function line(slide,x,y,w,h=0,color=C.border,width=0.8){return slide.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width,style:'solid'}});}
export function tag(slide,text,x,y,w,h,fill=C.tab,size=18){rect(slide,x,y,w,h,fill);txt(slide,text,x+5,y+1,w-10,h-2,size,'#FFFFFF',true,'center');}
export function panel(slide,title,x,y,w,h,{tabWidth=145,tabHeight=26,fill='#FFFFFF',size=20}={}){
  rect(slide,x,y+tabHeight-7,w,h-tabHeight+7,fill,C.border,1.1,'panel');
  tag(slide,title,x-2,y,tabWidth,tabHeight,C.tab,size);
  return {x:x+10,y:y+tabHeight+12,w:w-20,h:h-tabHeight-22};
}
export function cell(slide,text,x,y,w,h,{fill=C.paleBlue,size=11,color=C.ink,bold=false,border='#BCD0DF'}={}){
  const s=rect(slide,x,y,w,h,fill,border,0.65,'cell'); s.text=text;
  s.text.style={fontSize:size,typeface:FONT,color,bold,alignment:'center',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:2,lineSpacing:1.05};return s;
}
export function arrow(slide,x,y,w,h,color=C.blue){return slide.shapes.add({geometry:'rightArrow',position:{left:x,top:y,width:w,height:h},fill:color,line:{fill:'none',width:0}});}
// Fallback only: source-page reuse is preferred. Logo bytes must be from the current template.
export function header(slide,title,logo,{project=false}={}){
  if(project)throw Error('Legacy project navigation is retired; use the bundled internal-report template.');
  slide.background.fill='#FFFFFF';
  txt(slide,title,17.34,12.80,1078.19,43.52,32,C.blue,true,'left',
    {wrap:'none',verticalAlignment:'middle',insets:{left:9.6,right:9.6,top:4.8,bottom:4.8}});
  if(logo)slide.images.add({blob:logo,contentType:'image/png',alt:'中国移动新模板原始标识',
    position:{left:959.38,top:-48.38,width:292.82,height:164.71},fit:'contain'});
}
// Explicit line breaking keeps dense CJK copy predictable across renderers.
// This is only a sizing heuristic; render checks are still required.
export function wrapCjk(text,width,size){
  const units=s=>[...s].reduce((n,ch)=>n+(/[\u0000-\u007f]/.test(ch)?(/[MW@]/.test(ch)?1:/[A-Z]/.test(ch)?0.76:/[a-z0-9]/.test(ch)?0.64:/\s/.test(ch)?0.4:0.5):1),0);
  const cap=width/size-1.2,closing=/^[，。；：？！、）》”’%.,;:!?)]$/;
  const lines=[];
  for(const p of text.split('\n')){
    let cur='',u=0;
    for(const token of (p.match(/[A-Za-z0-9]+(?:[.,_-][A-Za-z0-9]+)*|[\s\S]/g)||[])){
      const k=units(token);
      if(cur&&u+k>cap&&!closing.test(token)){lines.push(cur.trimEnd());cur='';u=0;}
      cur+=token;u+=k;
    }
    lines.push(cur.trimEnd());
  }
  return lines;
}
export function prose(slide,text,x,y,w,{size=11.3,lineHeight=19,color=C.ink,bold=false}={}){
  const lines=wrapCjk(text,w,size);for(let i=0;i<lines.length;i++)txt(slide,lines[i],x,y+i*lineHeight,w,lineHeight+1,size,color,bold,'left',{wrap:'none'});return y+lines.length*lineHeight;
}
export function nativeTable(slide,values,x,y,w,h,{widths,size=10.5,headerSize=size}={}){
  const t=slide.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,...(widths?{columnWidths:widths}: {})});
  t.borders.assign({fill:'#8BB3D1',width:0.65,style:'solid'});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[r].length;c++){
    const v=t.getCell(r,c);v.fill=r===0?C.blue:r%2? '#FFFFFF':'#EDF4F9';
    v.text.style={typeface:FONT,fontSize:r===0?headerSize:size,color:r===0?'#FFFFFF':C.ink,bold:r===0,alignment:c===0?'center':'left',verticalAlignment:'middle',insets:3,autoFit:'none',wrap:'square',lineSpacing:1.04};
  }
  return t;
}
