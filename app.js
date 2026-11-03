const $ = (id) => document.getElementById(id);
let token = null, anim = null, localStart = null, elapsedDisplay = 0, finished = false;
const clock = $('clock');
function fmt(ms){ return (ms/1000).toFixed(3); }
function paintClock(){ if(localStart !== null && !finished){ elapsedDisplay = performance.now()-localStart; clock.innerHTML = `${fmt(elapsedDisplay)}<span>s</span>`; anim=requestAnimationFrame(paintClock); } }
async function refreshStatus(){
  try { const r=await fetch('/api/status'); const s=await r.json();
    $('target').textContent=s.target_seconds;
    if(s.has_winner){ $('todayWinner').textContent=`🏆 ${s.winner_name} — ₹${s.prize}`; $('statusPill').textContent='CLOSED'; $('statusPill').className='pill closed'; $('startBtn').disabled=true; $('hint').textContent='आज का विजेता चुना जा चुका है। कल वापस आएँ।'; }
    else if(!s.active){ $('statusPill').textContent='PAUSED'; $('startBtn').disabled=true; }
  } catch(e){ $('hint').textContent='सर्वर से कनेक्शन नहीं हो पाया। पेज रीफ्रेश करें।'; }
}
$('startBtn').addEventListener('click', async ()=>{
  $('startBtn').disabled=true; $('result').classList.add('hidden'); $('upiForm').classList.add('hidden');
  try { const r=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('playerName').value.trim()||'Instagram Player'})}); const d=await r.json();
    if(!r.ok) throw new Error(d.error||'गेम शुरू नहीं हुआ'); token=d.token; finished=false; localStart=performance.now(); $('stopBtn').disabled=false; $('statusPill').textContent='PLAYING'; $('statusPill').className='pill playing'; $('hint').textContent='अब सही समय पर STOP TIMER दबाएँ!'; anim=requestAnimationFrame(paintClock);
  } catch(e){ showResult(e.message); $('startBtn').disabled=false; }
});
$('stopBtn').addEventListener('click', async ()=>{
  if(!token || finished) return; finished=true; cancelAnimationFrame(anim); $('stopBtn').disabled=true; $('clock').textContent=`${fmt(elapsedDisplay)}s`;
  try { const r=await fetch('/api/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})}); const d=await r.json(); if(!r.ok) throw new Error(d.error||'नतीजा नहीं मिल पाया');
    showResult(`${d.message}${d.elapsed_ms!==undefined?` आपका सर्वर-रिकॉर्ड समय: ${fmt(d.elapsed_ms)} सेकंड।`:''}`);
    if(d.result==='winner'){ $('statusPill').textContent='WINNER'; $('statusPill').className='pill winner'; $('upiForm').classList.remove('hidden'); $('todayWinner').textContent=`🏆 ${$('playerName').value.trim()||'Instagram Player'} — ₹100`; }
    else if(d.result==='closed'){ $('statusPill').textContent='CLOSED'; $('statusPill').className='pill closed'; }
    else { $('statusPill').textContent='FINISHED'; $('statusPill').className='pill neutral'; }
    refreshStatus();
  } catch(e){ showResult(e.message); }
});
$('upiForm').addEventListener('submit',async (e)=>{ e.preventDefault(); try { const r=await fetch('/api/upi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,upi_id:$('upiId').value.trim()})}); const d=await r.json(); if(!r.ok) throw new Error(d.error||'सबमिट नहीं हुआ'); showResult(d.message); $('upiForm').classList.add('hidden'); } catch(e){ showResult(e.message); }});
function showResult(msg){ $('result').textContent=msg; $('result').classList.remove('hidden'); }
refreshStatus();
