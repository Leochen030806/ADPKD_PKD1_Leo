/* ============================================================================
 *  make_str_slide.js  —  PKD1 PGT-M CE report slides
 *  2 pages / STR · 8 samples / page · per-sample rows
 *  + auto-crops the full-trace thumbnails to <=510 bp (drops the empty >500 bp tail)
 *  + identifies each sample BY READING THE LABEL IN THE IMAGE (OCR) and re-orders
 *    to the fixed reference sequence, so screenshots may be in ANY order.
 * ----------------------------------------------------------------------------
 *  npm install pptxgenjs xlsx sharp tesseract.js      # one time
 *  node make_str_slide.js 11                          # STR 11  (2 slides)
 *  node make_str_slide.js 3 5 7 8 11                  # batch
 *
 *  Edit CONFIG so the paths point at your Desktop.  Windows: use forward slashes.
 *  OCR uses Tesseract's bundled English data (downloaded once by tesseract.js);
 *  if the machine is offline, set TESSDATA to a folder holding eng.traineddata.
 * ========================================================================== */

const CONFIG = {
  XLSX  : "C:/Users/e1638543/Desktop/PKD1_CE_summary_robust.xlsx",
  IMGDIR: "C:/Users/e1638543/Desktop/CE screen shoot",
  OUTDIR: "C:/Users/e1638543/Desktop",
  SHEET : "CE Summary",
  CROP_BP: 510,     // crop the full-trace thumbnail at this size (bp)
  BP_SPAN: 773,     // bp span of the GeneMapper x-axis view (0 .. BP_SPAN across the frame)
  TESSDATA: null,   // e.g. "C:/tessdata" for offline; null = let tesseract.js fetch 'eng'
  EXAMPLE: {},      // optional per-page pin, e.g. {"1299a":"NA03815","1299b":"NA09133"}
  OUTNAME: null,    // override the combined-deck filename (without .pptx)
};

// --- CLI / env overrides so the paths don't have to be edited in source -------------
// e.g. node make_str_slide.js --xlsx ./sum.xlsx --imgdir ./img --outdir ./out --combined 3 5
(function applyOverrides(){
  const a=process.argv.slice(2);
  const flag=(name)=>{ const i=a.indexOf('--'+name); return i>=0&&a[i+1]&&!a[i+1].startsWith('--')?a[i+1]:null; };
  const map={xlsx:'XLSX',imgdir:'IMGDIR',outdir:'OUTDIR',sheet:'SHEET',tessdata:'TESSDATA',outname:'OUTNAME'};
  for(const [f,k] of Object.entries(map)){ const v=flag(f)||process.env['CE_'+k]; if(v) CONFIG[k]=v; }
  const n=flag('cropbp')||process.env.CE_CROP_BP; if(n) CONFIG.CROP_BP=+n;
  const s=flag('bpspan')||process.env.CE_BP_SPAN; if(s) CONFIG.BP_SPAN=+s;
})();

const fs    = require("fs");
const path  = require("path");

// Node resolves node_modules from the SCRIPT's folder upward, so a script kept in a skill
// directory can't see packages installed in the working directory. Fall back to CWD.
function req(name){
  try{ return require(name); }catch(e){
    for(const base of [process.cwd(), path.join(process.cwd(),"node_modules")]){
      try{ return require(path.join(base,"node_modules",name)); }catch(_){}
      try{ return require(path.join(base,name)); }catch(_){}
    }
    console.error(`\nMissing dependency "${name}".  Install once, in the folder you run this from:\n`+
                  `    npm install pptxgenjs xlsx sharp tesseract.js\n`);
    process.exit(1);
  }
}
const XLSX  = req("xlsx");
const sharp = req("sharp");
const pptx  = req("pptxgenjs");
const { createWorker } = req("tesseract.js");

const INK="12303F", TEAL="1C7293", ACC="02C39A", PANEL="EDF3F5",
      MUTE="5E6E76", LINE="D5E0E4", HET=TEAL, HOM="8A97A0", WHITE="FFFFFF",
      F="Calibri", FS="Cambria";

// Fixed reference sequence — the order every deck is re-arranged into.
const SAMPLE_ORDER = [
  "NA03814","NA03815","NA04738","NA04776","NA04820","NA06075","NA06890","NA07425",
  "NA07426","NA07428","NA09133","NA11518","NA16243","NA17942","NA22601","NA50194"];
const KD = Object.fromEntries(SAMPLE_ORDER.map(k=>[k,k.slice(2)]));

// ===================== spreadsheet =====================
// Accepts either the STR number (column A) or the marker number (column B).
function readSTR(key){
  const wb=XLSX.readFile(CONFIG.XLSX), ws=wb.Sheets[CONFIG.SHEET];
  const cell=(r,c)=>{const v=ws[XLSX.utils.encode_cell({r:r-1,c:c-1})];return v?v.v:null;};
  let row=null;
  for(let r=5;r<=17;r++){ if(String(cell(r,1))===String(key)){row=r;break;} }          // STR no.
  if(!row) for(let r=5;r<=17;r++){ if(String(cell(r,2))===String(key)){row=r;break;} } // marker no.
  if(!row) throw new Error(`STR / marker "${key}" not found in ${CONFIG.SHEET}`);
  const strNo=cell(row,1);
  const marker=cell(row,2), repeat=cell(row,3), repLen=(repeat||"AATG").length;
  const samples={};
  SAMPLE_ORDER.forEach((s,i)=>{ const a1=cell(row,4+i*2),a2=cell(row,5+i*2);
    samples[s]={a1:a1==null?null:+a1,a2:a2==null?null:+a2}; });
  const typed=cell(row,36),nAll=cell(row,37),het=cell(row,38);
  const observed=String(cell(row,39)||"").split(",").map(x=>+x.trim()).filter(x=>!isNaN(x));
  const snap=v=>observed.reduce((b,a)=>Math.abs(a-v)<Math.abs(b-v)?a:b,observed[0]);
  // zoom bp window = main allele cluster (drops far outliers), rounded to 5
  const srt=[...observed].sort((a,b)=>a-b), med=srt.length?srt[Math.floor(srt.length/2)]:250;
  const clust=srt.filter(a=>Math.abs(a-med)<=40);
  const zLo=clust.length?Math.floor((Math.min(...clust)-6)/5)*5:240;
  const zHi=clust.length?Math.ceil((Math.max(...clust)+6)/5)*5:260;
  for(const s of SAMPLE_ORDER){ const o=samples[s];
    if(o.a1==null){o.call=null;o.tag=null;continue;}
    const b1=snap(o.a1);
    if(o.a2==null){o.call=String(b1);o.tag="hom";}
    else{const b2=snap(o.a2),lo=Math.min(b1,b2),hi=Math.max(b1,b2);
      o.call=lo===hi?String(lo):`${lo}/${hi}`; o.tag=lo===hi?"hom":"het";} }
  return {strNo,marker,repeat,repLen,samples,typed,nAll,
          hetPct:(het!=null?(het*100).toFixed(1)+"%":"—"),observed,
          zLo,zHi,zoomRange:`≈${zLo}–${zHi} bp`};
}

// ===================== image geometry =====================
const _bands={}, _frame={};
async function panelBands(file){
  if(_bands[file]) return _bands[file];
  const img=sharp(file), {width:W,height:H}=await img.metadata();
  const raw=await img.clone().removeAlpha().raw().toBuffer();
  const grayRow=y=>{let n=0,t=0;for(let x=0;x<W;x+=4){t++;const i=(y*W+x)*3,r=raw[i],g=raw[i+1],b=raw[i+2];
      if(Math.abs(r-g)<12&&Math.abs(g-b)<12&&r>205&&r<250)n++;} return n/t>0.6;};
  const bars=[]; let run=null;
  for(let y=0;y<H;y++){ if(grayRow(y)){run?run[1]=y:run=[y,y];} else if(run){bars.push(run);run=null;} }
  if(run)bars.push(run);
  let gaps=[]; for(let i=0;i<bars.length-1;i++){const a=bars[i][1],b=bars[i+1][0];if(b-a>40)gaps.push([a+2,b-1]);}
  // Screenshots are sometimes cut short so the LAST panel has no gray bar under it — the
  // region below the final bar is still a full plot, so keep it as a candidate.
  if(bars.length){ const last=bars[bars.length-1][1]; if(H-last>40) gaps.push([last+2,H-1]); }
  gaps.sort((p,q)=>(q[1]-q[0])-(p[1]-p[0])); gaps=gaps.slice(0,3).sort((p,q)=>p[0]-q[0]);
  return _bands[file]={W,H,panels:gaps};
}
// leftmost / rightmost near-black vertical frame lines (x for 0 bp and BP_SPAN bp)
async function frameX(file){
  if(_frame[file]) return _frame[file];
  const {W,panels}=await panelBands(file); const [y0,y1]=panels[0];
  const raw=await sharp(file).removeAlpha().raw().toBuffer();
  const blackCol=x=>{let n=0;for(let y=y0;y<y1;y++){const i=(y*W+x)*3;if(raw[i]<90&&raw[i+1]<90&&raw[i+2]<90)n++;}return n/(y1-y0)>0.7;};
  let xs=[]; for(let x=0;x<W;x++) if(blackCol(x)) xs.push(x);
  return _frame[file]={xL:xs.length?xs[0]:Math.round(W*0.048), xR:xs.length?xs[xs.length-1]:Math.round(W*0.955)};
}
async function peakXRange(file,y0,y1){
  const {width:W}=await sharp(file).metadata();
  const raw=await sharp(file).removeAlpha().raw().toBuffer();
  let lo=W,hi=0;
  for(let x=0;x<W;x++){let hits=0;
    for(let y=y0;y<y1;y++){const i=(y*W+x)*3,r=raw[i],g=raw[i+1],b=raw[i+2];
      const strong=Math.max(r,g,b)-Math.min(r,g,b)>70 && Math.max(r,g,b)>120;
      const orange=r>200 && g>=105 && g<=190 && b<100;      // LIZ/GeneScan size standard — ignore
      const cyan=g>180 && b>180 && r<120;                   // cyan highlight border of the active panel — ignore
      if(strong && !orange && !cyan) hits++;}
    if(hits>=3){lo=Math.min(lo,x);hi=Math.max(hi,x);}}
  if(hi<=lo)return null; const pad=Math.round((hi-lo)*0.35);
  return [Math.max(0,lo-pad),Math.min(W,hi+pad)];
}
const isWide = async f => (await sharp(f).metadata()).width>1000;
const dim = async f => { const m=await sharp(f).metadata(); return [m.width,m.height]; };

// crop one panel; for the full-trace thumbnail also cut the empty >CROP_BP tail
async function cropPanel(file,k,out,cropBp){
  const {W,panels}=await panelBands(file); const [y0,y1]=panels[k]||panels[panels.length-1];
  let width=W-6;
  if(cropBp){ const {xL,xR}=await frameX(file); width=Math.min(W, Math.round(xL+(cropBp/CONFIG.BP_SPAN)*(xR-xL))); }
  await sharp(file).extract({left:0,top:y0,width,height:y1-y0}).toFile(out); return out;
}
async function cropExample(file,k,out){
  const {panels}=await panelBands(file); const [y0,y1]=panels[k]||panels[panels.length-1];
  const xr=await peakXRange(file,y0,y1)||[0,(await sharp(file).metadata()).width];
  await sharp(file).extract({left:xr[0],top:y0,width:xr[1]-xr[0],height:y1-y0}).toFile(out); return out;
}
// common peak window (as a fraction of the plot) across all genotyped samples' zoom panels,
// so wide zoom screenshots get cropped to the informative peaks with a consistent x-scale.
async function zoomPeakWindow(D,map){
  let fLo=1,fHi=0,any=false;
  for(const s of SAMPLE_ORDER){ const pz=map[s].zoom; if(!pz||!D.samples[s].call) continue;
    const zf=pz.file; const {panels}=await panelBands(zf); const [y0,y1]=panels[pz.k]||panels[panels.length-1];
    const pr=await peakXRange(zf,y0,y1); if(!pr) continue; const {xL,xR}=await frameX(zf);
    const a=(pr[0]-xL)/(xR-xL), b=(pr[1]-xL)/(xR-xL); if(b-a>0.8) continue;  // skip detection failures
    fLo=Math.min(fLo,a); fHi=Math.max(fHi,b); any=true; }
  if(!any||fHi<=fLo) return null; const pad=0.06;
  return [Math.max(0,fLo-pad),Math.min(1,fHi+pad)];
}
// crop a zoom panel: wide screenshots -> to the common peak window; narrow ones -> full panel
async function cropZoom(file,k,out,frac){
  const {W,panels}=await panelBands(file); const [y0,y1]=panels[k]||panels[panels.length-1];
  let left=0,width=W-6;
  if(frac && W>1000){ const {xL,xR}=await frameX(file);
    left=Math.max(0,Math.round(xL+frac[0]*(xR-xL))); width=Math.min(W-left,Math.round((frac[1]-frac[0])*(xR-xL))); }
  await sharp(file).extract({left,top:y0,width:Math.max(20,width),height:y1-y0}).toFile(out); return out;
}

// ===================== OCR sample identification =====================
function digitsOf(s){s=s.toUpperCase();const m={O:'0',Q:'0',D:'0',B:'8',I:'1',L:'1',S:'5',G:'6',Z:'2',A:'4'};
  return [...s].map(c=>m[c]||c).join('').replace(/[^0-9]/g,'');}
function cutDate(s){for(const a of['2026','2027','0260','260','026']){const i=s.indexOf(a);if(i>=4)return s.slice(0,i);}return s;}
function lcs(a,b){const m=Array.from({length:a.length+1},()=>Array(b.length+1).fill(0));
  for(let i=0;i<a.length;i++)for(let j=0;j<b.length;j++)m[i+1][j+1]=a[i]===b[j]?m[i][j]+1:Math.max(m[i][j+1],m[i+1][j]);
  return m[a.length][b.length];}
async function ocrStreams(worker,file,y0,y1){
  const streams=[];
  for(const [x0,w] of [[0,232],[232,190]]){
    for(const bin of [false,true]){
      let p=sharp(file).extract({left:x0,top:y0,width:w,height:Math.max(6,y1-y0)}).resize({width:w*4});
      if(bin) p=p.grayscale().threshold(140);
      const {data:{text}}=await worker.recognize(await p.toBuffer(),{},{text:true});
      streams.push(cutDate(digitsOf(text)));
      if(!bin && SAMPLE_ORDER.some(k=>streams[streams.length-1].includes(KD[k]))) return streams; // early exit on exact hit
    }
  }
  return streams;
}
const exactHit=streams=>SAMPLE_ORDER.find(k=>streams.some(s=>s.includes(KD[k])))||null;
const fuzzy=(streams,s)=>Math.max(...streams.map(x=>lcs(x,KD[s])));

// Sample indices encoded in the filename, e.g. "8-16_9_5" / "16_9_5" -> [16,9,5] (panel order).
// `prefixes` are stripped first (marker no., STR no.) so "2290-1_2_3" and "1_2_3" both work.
function idxFromName(file,prefixes){
  let b=path.basename(file).replace(/\.png$/i,'').replace(/-z$/i,'').replace(/[_-]?zoom.*$/i,'');
  for(const p of prefixes){ if(p==null) continue;
    const m=b.match(new RegExp('^'+p+'[-_]?(.*)$','i')); if(m){ b=m[1]; break; } }
  b=b.replace(/^(thumb(nail)?|orig(inal)?|full)[-_]?/i,'');
  const parts=b.split(/[_\-]+/).filter(x=>/^\d+$/.test(x)).map(Number);
  if(!parts.length) return null;
  if(parts.some(n=>n<1||n>SAMPLE_ORDER.length)) return null;
  if(new Set(parts).size!==parts.length) return null;
  return parts;
}

// OCR a list of images' panels -> {sample: {file,k}}.
// Priority: (1) sample indices encoded in the filename — authoritative, because the CE run's
// on-screen labels can be wrong; (2) exact OCR label match; (3) constrained fuzzy fallback.
async function identifyPanels(worker,files,prefixes){
  const panels=[];
  for(const {file,rel} of files){ const {panels:bands}=await panelBands(file);
    const hint=idxFromName(rel,prefixes); const useHint=hint&&hint.length===bands.length;
    for(let k=0;k<bands.length;k++){ const plotTop=bands[k][0];         // label is in the gray bar ABOVE the plot
      const st=await ocrStreams(worker,file,Math.max(0,plotTop-24),plotTop-2);
      panels.push({file,rel,k,streams:st,exact:exactHit(st),hint:useHint?SAMPLE_ORDER[hint[k]-1]:null}); } }
  const map={},how={},used=new Set(),warn=[];
  for(const p of panels){ if(p.hint && !(p.hint in map)){ map[p.hint]={file:p.file,rel:p.rel,k:p.k}; used.add(p); how[p.hint]="named";
      if(p.exact&&p.exact!==p.hint) warn.push(`${p.rel} p${p.k+1}: on-screen label reads ${p.exact}, filename says ${p.hint} — using ${p.hint}`); } }
  for(const p of panels){ if(used.has(p))continue;
    if(p.exact && !(p.exact in map)){ map[p.exact]={file:p.file,rel:p.rel,k:p.k}; used.add(p); how[p.exact]="read"; } }
  // Fuzzy fallback only among panels that were NOT positively identified. A panel whose label
  // read as an already-assigned sample is a duplicate (overlapping capture windows), not an
  // unknown — letting it compete would steal a slot from the sample it doesn't show.
  for(const s of SAMPLE_ORDER){ if(s in map) continue;
    let best=null,bs=-1; for(const p of panels){ if(used.has(p)||p.exact||p.hint)continue; const sc=fuzzy(p.streams,s); if(sc>bs){bs=sc;best=p;} }
    if(best){ map[s]={file:best.file,rel:best.rel,k:best.k}; used.add(best); how[s]="inferred"; } }
  return {map,how,warn};
}

// ===================== deck =====================
// Prepare one STR's data + cropped images into `work` (filenames namespaced by strNo). Returns {D,S} or null.
// Where this marker's screenshots live. Preferred layout is one folder per marker:
//   <IMGDIR>/2290/...   (the STR number also works as a folder name)
// Legacy flat layout (<IMGDIR>/5-1_2_3.PNG) is still supported.
function walkPngs(root){
  const out=[];
  (function rec(d){ for(const e of fs.readdirSync(d,{withFileTypes:true})){
      const p=path.join(d,e.name);
      if(e.isDirectory()) rec(p);
      else if(/\.png$/i.test(e.name)) out.push({file:p, rel:path.relative(root,p).replace(/\\/g,"/")});
  }})(root);
  return out.sort((a,b)=>a.rel.localeCompare(b.rel));
}
function findImages(strNo,marker){
  for(const folder of [String(marker),String(strNo)]){
    const dir=path.join(CONFIG.IMGDIR,folder);
    if(fs.existsSync(dir)&&fs.statSync(dir).isDirectory()){
      const files=walkPngs(dir);                  // recursive: thumbnail/ and zoom/ both work
      if(files.length) return {dir,files};
    }
  }
  const re=new RegExp('^('+marker+'|'+strNo+')[-_]','i');
  return {dir:CONFIG.IMGDIR,
          files:fs.readdirSync(CONFIG.IMGDIR).filter(f=>re.test(f)&&/\.png$/i.test(f))
                  .map(f=>({file:path.join(CONFIG.IMGDIR,f), rel:f}))};
}
// zoom if the -z suffix is on the name, or "zoom" appears anywhere in the relative path
const isZoomFile=rel=>/-z\.png$/i.test(rel)||/zoom/i.test(rel);

async function prepare(key,work){
  const D=readSTR(key);
  if(D.typed==null){ console.log(`STR ${D.strNo} (Marker ${D.marker}): no data in sheet — skipped.`); return null; }

  const {dir,files}=findImages(D.strNo,D.marker);
  const origs=files.filter(f=>!isZoomFile(f.rel));
  const zooms=files.filter(f=>isZoomFile(f.rel));
  if(!origs.length){ console.log(`STR ${D.strNo} (Marker ${D.marker}): no images found in ${dir} — skipped.`); return null; }
  const prefixes=[D.marker,D.strNo];

  // Identify samples by OCR — originals and zooms are matched by IMAGE CONTENT, not filename,
  // so mismatched / underscore / "empty" names still line up correctly.
  const worker=await createWorker('eng',1,
    CONFIG.TESSDATA?{langPath:CONFIG.TESSDATA,gzip:false,cacheMethod:'none'}:{});
  const O=await identifyPanels(worker,origs,prefixes);
  const Z=zooms.length?await identifyPanels(worker,zooms,prefixes):{map:{},how:{},warn:[]};
  await worker.terminate();
  const map={},how={};
  for(const s of SAMPLE_ORDER){ map[s]={orig:O.map[s]||null, zoom:Z.map[s]||null};
    how[s]={orig:O.how[s]||"missing", zoom:Z.how[s]||"missing"}; }
  console.log(`STR ${D.strNo} (Marker ${D.marker})  images: ${dir}`);
  console.log(`  identification (orig | zoom):`);
  for(const s of SAMPLE_ORDER){ const o=map[s].orig,z=map[s].zoom;
    const flag=D.samples[s].call==null?"  (no genotype)":"";
    console.log(`  ${s}: ${o?o.rel+' p'+(o.k+1)+' ['+how[s].orig+']':'—'}  |  ${z?z.rel+' p'+(z.k+1)+' ['+how[s].zoom+']':'—'}${flag}`); }
  const warns=[...(O.warn||[]),...(Z.warn||[])];
  if(warns.length){ console.log(`  ! label/filename mismatches (filename wins):`); warns.forEach(w=>console.log(`    ${w}`)); }

  // crop each sample's thumbnail (<=CROP_BP) + zoom (wide zooms -> common peak window)
  const zwin=await zoomPeakWindow(D,map);
  const S={};
  for(const s of SAMPLE_ORDER){ S[s]={orig:null,zoom:null}; const po=map[s].orig, pz=map[s].zoom;
    if(po) S[s].orig=await cropPanel(po.file,po.k,path.join(work,`o_${D.strNo}_${s}.png`),CONFIG.CROP_BP);
    if(pz) S[s].zoom=await cropZoom(pz.file,pz.k,path.join(work,`z_${D.strNo}_${s}.png`),zwin); }
  return {D,S};
}
function newDeck(){ const p=new pptx(); p.defineLayout({name:"PORT",width:7.5,height:13.33}); p.layout="PORT"; return p; }
async function addPages(p,D,S){
  await drawPage(p,D,S,null,null,SAMPLE_ORDER.slice(0,8),"1","1 – 8",D.marker+"a");
  await drawPage(p,D,S,null,null,SAMPLE_ORDER.slice(8),"2","9 – 16",D.marker+"b");
}
// Every marker/STR in the sheet that has both data and an image folder, in STR order.
function discoverMarkers(){
  const wb=XLSX.readFile(CONFIG.XLSX), ws=wb.Sheets[CONFIG.SHEET];
  const cell=(r,c)=>{const v=ws[XLSX.utils.encode_cell({r:r-1,c:c-1})];return v?v.v:null;};
  const out=[];
  for(let r=5;r<=17;r++){
    const strNo=cell(r,1), marker=cell(r,2), typed=cell(r,36);
    if(strNo==null||marker==null) continue;
    const {files}=findImages(strNo,marker);
    const ready=typed!=null && files.length>0;
    out.push({strNo,marker,typed,nFiles:files.length,ready});
  }
  return out;
}
function reportDiscovery(rows){
  console.log(`Scanning ${CONFIG.IMGDIR}`);
  for(const r of rows){
    const why = r.nFiles===0 ? "no image folder" : (r.typed==null ? "no data in sheet" : `${r.nFiles} images`);
    console.log(`  STR ${String(r.strNo).padStart(2)} · Marker ${r.marker}: ${r.ready?"READY":"skip"}  (${why})`);
  }
  const ready=rows.filter(r=>r.ready);
  console.log(`  -> ${ready.length} marker(s) ready: ${ready.map(r=>r.marker).join(", ")||"none"}\n`);
  return ready;
}
// one .pptx per marker
async function buildDeck(key){
  const work=path.join(CONFIG.OUTDIR,`_ce_tmp_${key}`); fs.mkdirSync(work,{recursive:true});
  try{ const prep=await prepare(key,work); if(!prep) return;
    const p=newDeck(); await addPages(p,prep.D,prep.S);
    const out=path.join(CONFIG.OUTDIR,`PKD1_Marker${prep.D.marker}_CE_EN.pptx`);
    await p.writeFile({fileName:out}); console.log("WROTE",out);
  } finally { fs.rmSync(work,{recursive:true,force:true}); }
}
// all requested STRs in ONE .pptx (2 pages each), in the given order
async function buildCombined(list){
  const work=path.join(CONFIG.OUTDIR,`_ce_tmp_combined`); fs.mkdirSync(work,{recursive:true});
  try{ const p=newDeck(); const done=[];
    for(const n of list){ const prep=await prepare(n,work); if(!prep) continue; await addPages(p,prep.D,prep.S); done.push(prep.D.marker); }
    if(!done.length){ console.log("Nothing to combine."); return; }
    const out=path.join(CONFIG.OUTDIR,`${CONFIG.OUTNAME||"PKD1_STR_panel_CE_EN"}.pptx`);
    await p.writeFile({fileName:out}); console.log(`WROTE ${out}  (markers: ${done.join(", ")}, ${done.length*2} slides)`);
  } finally { fs.rmSync(work,{recursive:true,force:true}); }
}

async function drawPage(p,D,S,map,work,names,partNo,partLabel,pinKey){
  const s=p.addSlide(); s.background={color:WHITE};
  const fitW=(pw,ph,w)=>({w,h:+(w*ph/pw).toFixed(3)});
  const fitH=(pw,ph,h)=>({w:+(h*pw/ph).toFixed(3),h});
  const fitBox=(pw,ph,mw,mh)=>{const sc=Math.min(mw/pw,mh/ph);return {w:+(pw*sc).toFixed(3),h:+(ph*sc).toFixed(3)};};
  const frame=(x,y,w,h)=>s.addShape("roundRect",{x,y,w,h,rectRadius:0.03,fill:{type:"none"},line:{color:LINE,width:0.75}});

  s.addText("PKD1 STR PANEL · CE GENOTYPING SUMMARY",{x:0.35,y:0.28,w:6.8,h:0.26,fontFace:F,fontSize:10.5,bold:true,color:TEAL,charSpacing:2,margin:0});
  s.addText([{text:`STR ${D.strNo}`,options:{fontFace:FS,fontSize:29,bold:true,color:INK}},
             {text:"   ·   ",options:{fontFace:FS,fontSize:29,color:LINE}},
             {text:`Marker ${D.marker}`,options:{fontFace:FS,fontSize:29,bold:true,color:TEAL}}],
            {x:0.32,y:0.52,w:4.7,h:0.58,valign:"middle",margin:0});
  s.addShape("roundRect",{x:5.15,y:0.58,w:2.0,h:0.48,rectRadius:0.1,fill:{color:INK},line:{type:"none"}});
  s.addText([{text:"Repeat unit  ",options:{fontFace:F,fontSize:10,color:"BFD3DB"}},
             {text:`(${D.repeat})n`,options:{fontFace:FS,fontSize:13,bold:true,color:WHITE,italic:true}}],
            {x:5.15,y:0.58,w:2.0,h:0.48,align:"center",valign:"middle",margin:0});
  s.addShape("roundRect",{x:0.35,y:1.14,w:2.15,h:0.30,rectRadius:0.15,fill:{color:PANEL},line:{color:LINE,width:0.75}});
  s.addText(`Page ${partNo} / 2  ·  Samples ${partLabel}`,{x:0.35,y:1.14,w:2.15,h:0.30,align:"center",valign:"middle",fontFace:F,fontSize:9,bold:true,color:TEAL,margin:0});

  const cardY=1.60,cardH=0.92;
  const card=(x,w,big,bs,lab)=>{ s.addShape("roundRect",{x,y:cardY,w,h:cardH,rectRadius:0.06,fill:{color:PANEL},line:{color:LINE,width:0.75}});
    s.addText(String(big),{x,y:cardY+0.10,w,h:0.46,align:"center",valign:"middle",fontFace:F,fontSize:bs,bold:true,color:INK,margin:0});
    s.addText(lab,{x,y:cardY+0.58,w,h:0.28,align:"center",valign:"middle",fontFace:F,fontSize:8.5,color:MUTE,margin:0}); };
  card(0.35,1.40,D.typed,26,"Samples typed (n)");
  card(1.85,1.40,D.nAll,26,"Alleles / locus");
  card(3.35,1.40,D.hetPct,22,"Heterozygosity (obs.)");
  s.addShape("roundRect",{x:4.90,y:cardY,w:2.25,h:cardH,rectRadius:0.06,fill:{color:PANEL},line:{color:LINE,width:0.75}});
  s.addText(D.observed.join(" · "),{x:4.90,y:cardY+0.10,w:2.25,h:0.46,align:"center",valign:"middle",fontFace:F,fontSize:15,bold:true,color:INK,margin:0});
  s.addText("Alleles observed (bp)",{x:4.90,y:cardY+0.58,w:2.25,h:0.28,align:"center",valign:"middle",fontFace:F,fontSize:8.5,color:MUTE,margin:0});

  let ex=CONFIG.EXAMPLE[pinKey];
  if(!ex){ const hets=names.filter(nm=>D.samples[nm].tag==="het"&&S[nm].zoom);
    const sp=nm=>{const c=D.samples[nm].call.split("/").map(Number);return Math.round((c[1]-c[0])/D.repLen);};
    ex=hets.filter(nm=>sp(nm)>=2).sort((a,b)=>sp(a)-sp(b))[0]||hets[0]; }
  const exY=2.62,exH=1.34;
  s.addShape("roundRect",{x:0.35,y:exY,w:6.8,h:exH,rectRadius:0.06,fill:{color:"F6FAFB"},line:{color:LINE,width:0.75}});
  if(ex && S[ex] && S[ex].zoom){
    const exImg=S[ex].zoom;                       // reuse this sample's already-cropped zoom (consistent framing)
    const [pw,ph]=await dim(exImg); let e=fitH(pw,ph,1.00); if(e.w>3.0) e=fitW(pw,ph,3.0);
    const eX=0.55,eY=exY+(exH-e.h)/2+0.05; s.addImage({path:exImg,x:eX,y:eY,w:e.w,h:e.h}); frame(eX,eY,e.w,e.h);
    s.addText("Representative heterozygote",{x:eX,y:exY+0.11,w:e.w,h:0.22,fontFace:F,fontSize:9,bold:true,color:TEAL,margin:0});
    const call=D.samples[ex].call;
    s.addText([{text:ex,options:{fontFace:F,fontSize:12.5,bold:true,color:INK,breakLine:true}},
               {text:`Alleles ${call?call.replace("/"," / "):""} bp`,options:{fontFace:F,fontSize:10,color:INK,breakLine:true}},
               {text:"Balanced peaks · well resolved · low stutter",options:{fontFace:F,fontSize:8.5,color:MUTE}}],
              {x:eX+e.w+0.22,y:exY+0.30,w:1.75,h:0.9,valign:"top",margin:0,lineSpacingMultiple:1.1}); }
  const lgX=5.55;
  s.addShape("roundRect",{x:lgX,y:exY+0.22,w:0.14,h:0.14,rectRadius:0.03,fill:{color:HET},line:{type:"none"}});
  s.addText("Heterozygous (het)",{x:lgX+0.22,y:exY+0.16,w:1.35,h:0.26,fontFace:F,fontSize:9.5,color:INK,valign:"middle",margin:0});
  s.addShape("roundRect",{x:lgX,y:exY+0.52,w:0.14,h:0.14,rectRadius:0.03,fill:{color:HOM},line:{type:"none"}});
  s.addText("Homozygous (hom)",{x:lgX+0.22,y:exY+0.46,w:1.35,h:0.26,fontFace:F,fontSize:9.5,color:INK,valign:"middle",margin:0});
  s.addText(`(${D.repeat})n · ${D.repLen} bp/repeat`,{x:lgX-0.02,y:exY+0.82,w:1.6,h:0.26,fontFace:F,fontSize:8.5,italic:true,color:MUTE,margin:0});

  s.addShape("rect",{x:0.35,y:4.16,w:0.11,h:0.20,fill:{color:ACC},line:{type:"none"}});
  s.addText(`Per-sample CE traces  ·  Samples ${partLabel}`,{x:0.54,y:4.08,w:6.6,h:0.32,fontFace:FS,fontSize:13.5,bold:true,color:INK,valign:"middle",margin:0});
  const hY=4.48;
  s.addText("Sample / genotype",{x:0.30,y:hY,w:1.4,h:0.22,fontFace:F,fontSize:8.5,bold:true,color:MUTE,margin:0});
  s.addText(`Raw electropherogram · full trace (0–${CONFIG.CROP_BP} bp)`,{x:1.40,y:hY,w:3.4,h:0.22,fontFace:F,fontSize:8.5,bold:true,color:MUTE,margin:0});
  s.addText(`Zoom · ${D.zoomRange}`,{x:4.90,y:hY,w:2.2,h:0.22,fontFace:F,fontSize:8.5,bold:true,color:MUTE,margin:0});

  const LX=0.30, LW=1.02, OX=1.40, ZX=4.90;
  let rowY=4.78; const pitch=1.00, block=0.86;
  for(const nm of names){
    const o=D.samples[nm];
    s.addShape("line",{x:0.30,y:rowY-0.04,w:6.85,h:0,line:{color:LINE,width:0.5}});
    const cy=rowY+block/2;
    s.addShape("roundRect",{x:LX,y:cy-0.30,w:0.10,h:0.10,rectRadius:0.02,fill:{color:o.tag==="het"?HET:HOM},line:{type:"none"}});
    s.addText(nm,{x:LX+0.16,y:cy-0.36,w:LW,h:0.24,fontFace:F,fontSize:10.5,bold:true,color:INK,valign:"middle",margin:0});
    s.addText([{text:(o.call||"—"),options:{fontFace:F,fontSize:11,bold:true,color:o.tag==="het"?HET:INK,breakLine:true}},
               {text:(o.tag||"—"),options:{fontFace:F,fontSize:8,color:MUTE}}],
              {x:LX+0.16,y:cy-0.06,w:LW,h:0.36,valign:"top",margin:0,lineSpacingMultiple:0.95});
    if(S[nm].orig){ const [pw,ph]=await dim(S[nm].orig); const im=fitBox(pw,ph,3.35,0.74);
      const iy=rowY+(block-im.h)/2; s.addImage({path:S[nm].orig,x:OX,y:iy,w:im.w,h:im.h}); frame(OX,iy,im.w,im.h); }
    else s.addText("(image pending)",{x:OX,y:rowY+block/2-0.1,w:3.35,h:0.2,align:"center",fontFace:F,fontSize:8,italic:true,color:HOM,margin:0});
    if(S[nm].zoom){ const [pw,ph]=await dim(S[nm].zoom); const im=fitBox(pw,ph,2.30,0.74);
      const iy=rowY+(block-im.h)/2; s.addImage({path:S[nm].zoom,x:ZX,y:iy,w:im.w,h:im.h}); frame(ZX,iy,im.w,im.h); }
    else s.addText("(zoom pending)",{x:ZX,y:rowY+block/2-0.1,w:2.30,h:0.2,align:"center",fontFace:F,fontSize:8,italic:true,color:HOM,margin:0});
    rowY+=pitch;
  }
  s.addShape("line",{x:0.30,y:rowY-0.04,w:6.85,h:0,line:{color:LINE,width:0.5}});
  s.addText(`PKD1 PGT-M STR linkage marker  ·  Marker ${D.marker} (STR ${D.strNo})  ·  GeneMapper / SeqStudio CE  ·  IDs read from image (OCR) · auto-binning ${D.repLen} bp (${D.repeat})`,
    {x:0.35,y:13.02,w:6.8,h:0.22,fontFace:F,fontSize:7.5,color:MUTE,margin:0});
}

// CLI
//   node make_str_slide.js --auto                  scan the image folder, rebuild the whole deck
//   node make_str_slide.js --list                  just report what's ready (no build)
//   node make_str_slide.js 2290                    one marker (marker no. or STR no.)
//   node make_str_slide.js --combined 2517 2290    those markers, in that order, one deck
//   path overrides: --xlsx <f> --imgdir <d> --outdir <d> --tessdata <d> --outname <name>
(async()=>{ const a=process.argv.slice(2);
  const has=re=>a.some(x=>re.test(x));
  const auto=has(/^--auto$/i), listOnly=has(/^--list$/i), combined=has(/^--(combined|all|merge)$/i);
  const valueFlags=new Set(['--xlsx','--imgdir','--outdir','--sheet','--tessdata','--outname','--cropbp','--bpspan']);
  const list=a.filter((x,i)=>/^\d+$/.test(x) && !(i>0 && valueFlags.has(a[i-1].toLowerCase())));
  try{
    if(listOnly){ reportDiscovery(discoverMarkers()); return; }
    if(auto){
      const ready=reportDiscovery(discoverMarkers());
      if(!ready.length){ console.log("Nothing to build."); return; }
      await buildCombined(ready.map(r=>r.marker));
      return;
    }
    if(!list.length){ console.error("Usage:  node make_str_slide.js --auto   |   ... 2290   |   ... --combined 2517 2290"); return; }
    if(combined) await buildCombined(list);
    else for(const n of list){ try{ await buildDeck(n); }catch(e){ console.error(`"${n}":`,e.message); } }
  }catch(e){ console.error(e.message,e.stack); } })();
