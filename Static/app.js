const $ = (id) => document.getElementById(id);
let token = null, anim = null, localStart = null, elapsedDisplay = 0, finished = false, stopResult = null;
let clientId = localStorage.getItem('giveaway_client_id');
if (!clientId) { clientId = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+'-'+Math.random().toString(36).slice(2)) + '-' + Math.random().toString(36).slice(2); localStorage.setItem('giveaway_client_id', clientId); }
const clock = $('clock');
function fmt(ms){ return (ms/1000).toFixed(3); }
function paintClock(){ if(localStart !== null && !finished){ elapsedDisplay = performance.now()-localStart; clock.innerHTML = `${fmt(elapsedDisplay)}<span>s</span>`; anim=requestAnimationFrame(paintClock); } }
async function refreshLeaderboard(){
  try { const r=await fetch('/api/leaderboard'); const d=await r.json();
    if(d.winner){ $('winnerName').textContent=`🥇 ${d.winner.name} — WINNER`; $('winnerTime').textContent=`Winning time: ${fmt(d.winner.elapsed_ms)} sec · Prize ₹${d.winner.prize}`; }
    else { $('winnerName').textContent='आज का विजेता अभी तय नहीं हुआ'; $('winnerTime').textContent='विजेता चुने जाने पर यहाँ सबसे ऊपर दिखेगा।'; }
    const list=d.leaderboard||[];
    $('leaderboard').innerHTML=list.length ? list.map((p,i)=>`<div class="leader-row ${i===0?'best':''}"><div class="leader-left"><span class="rank">${i===0?'🥇':i+1}</span><span class="leader-name">${escapeHtml(p.name)}${p.winner?' 🏆':''}</span></div><div class="leader-time">${fmt(p.elapsed_ms)} s<small>अंतर ${p.difference_ms} ms</small></div></div>`).join('') : '<p class="muted">अभी कोई टाइम रिकॉर्ड नहीं है।</p>';
  } catch(e) {}
}
function escapeHtml(s){return String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
async function refreshStatus(){
  try { const r=await fetch('/api/status'); const s=await r.json();
    $('target').textContent=s.target_seconds;
    if(s.has_winner){ $('todayWinner').textContent=`🏆 ${s.winner_name} — ₹${s.prize}`; $('statusPill').textContent='CLOSED'; $('statusPill').className='pill closed'; $('startBtn').disabled=true; $('hint').textContent='आज का विजेता चुना जा चुका है। कल वापस आएँ।'; }
    else if(!s.active){ $('statusPill').textContent='PAUSED'; $('startBtn').disabled=true; }
  } catch(e){ $('hint').textContent='सर्वर से कनेक्शन नहीं हो पाया। पेज रीफ्रेश करें।'; }
}
$('startBtn').addEventListener('click', async ()=>{
  $('startBtn').disabled=true; $('result').classList.add('hidden'); $('upiForm').classList.add('hidden');
  try { const r=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:clientId})}); const d=await r.json();
    if(!r.ok) throw new Error(d.error||'गेम शुरू नहीं हुआ'); token=d.token; finished=false; localStart=performance.now(); $('stopBtn').disabled=false; $('statusPill').textContent='PLAYING'; $('statusPill').className='pill playing'; $('hint').textContent='अब सही समय पर STOP TIMER दबाएँ!'; anim=requestAnimationFrame(paintClock);
  } catch(e){ showResult(e.message); $('startBtn').disabled=false; }
});
$('stopBtn').addEventListener('click', async ()=>{
  if(!token || finished) return; finished=true; cancelAnimationFrame(anim); $('stopBtn').disabled=true; $('clock').textContent=`${fmt(elapsedDisplay)}s`;
  try { const r=await fetch('/api/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})}); const d=await r.json(); if(!r.ok) throw new Error(d.error||'नतीजा नहीं मिल पाया');
    stopResult=d;
    showResult(`${d.message}${d.elapsed_ms!==undefined?` आपका सर्वर-रिकॉर्ड समय: ${fmt(d.elapsed_ms)} सेकंड।`:''}`);
    $('nameForm').classList.remove('hidden');
    if(d.result==='winner'){ $('statusPill').textContent='WINNER'; $('statusPill').className='pill winner'; }
    else if(d.result==='closed'){ $('statusPill').textContent='CLOSED'; $('statusPill').className='pill closed'; }
    else { $('statusPill').textContent='FINISHED'; $('statusPill').className='pill neutral'; }
    refreshStatus(); refreshLeaderboard();
  } catch(e){ showResult(e.message); }
});
$('nameForm').addEventListener('submit',async (e)=>{ e.preventDefault(); try { const r=await fetch('/api/name',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,name:$('playerName').value.trim()})}); const d=await r.json(); if(!r.ok) throw new Error(d.error||'नाम सबमिट नहीं हुआ'); showResult(d.message); $('nameForm').classList.add('hidden'); if(d.winner) $('upiForm').classList.remove('hidden'); refreshLeaderboard(); refreshStatus(); } catch(e){ showResult(e.message); }});
$('upiForm').addEventListener('submit',async (e)=>{ e.preventDefault(); try { const r=await fetch('/api/upi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,upi_id:$('upiId').value.trim()})}); const d=await r.json(); if(!r.ok) throw new Error(d.error||'सबमिट नहीं हुआ'); showResult(d.message); $('upiForm').classList.add('hidden'); } catch(e){ showResult(e.message); }});
function showResult(msg){ $('result').textContent=msg; $('result').classList.remove('hidden'); }
refreshStatus(); refreshLeaderboard();
