"""Small browser interface for the two local ActivityPub servers."""
from html import escape

from fastapi.responses import HTMLResponse


def demo_page(name: str, base: str) -> HTMLResponse:
    title = escape(name)
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PodcastHub · __TITLE__</title>
<style>
:root{font-family:system-ui,sans-serif;color:#172033;background:#f4f6fa}
body{max-width:1000px;margin:30px auto;padding:0 18px}
header{display:flex;justify-content:space-between;align-items:center}
main{display:grid;grid-template-columns:1fr 1fr;gap:16px}
section{background:white;border:1px solid #dbe2ec;border-radius:12px;padding:20px}
section.wide{grid-column:1/-1}
label{display:block;font-weight:600;margin-top:12px}
input,textarea,select,button{box-sizing:border-box;width:100%;padding:10px;border-radius:7px;border:1px solid #b6c3d4;font:inherit}
button{margin-top:14px;background:#164e84;color:white;border:0;cursor:pointer}
pre{white-space:pre-wrap;word-break:break-word;background:#101c2d;color:#d7e9f5;padding:14px;border-radius:8px;max-height:360px;overflow:auto;font-size:12px}
small{color:#546579}#status{min-height:22px}
@media(max-width:650px){main{grid-template-columns:1fr}section.wide{grid-column:1}}
</style></head><body>
<header><div><h1>PodcastHub</h1><p>__TITLE__ · ActivityPub federation lab</p></div><a href="/">Server home</a></header>
<main>
<section><h2>1. Follow another podcast</h2>
<small>Creates a Follow activity and sends it to the remote inbox.</small>
<label for="target">Remote actor</label>
<select id="target"><option value="http://127.0.0.1:8101/actors/podcast">Aurora :8101</option>
<option value="http://127.0.0.1:8102/actors/podcast">Orbit :8102</option></select>
<button onclick="follow()">Send Follow</button></section>
<section><h2>2. Publish an episode</h2>
<small>Creates an ActivityStreams Note and delivers it to followers.</small>
<label for="title">Episode title</label><input id="title" value="Hello, Fediverse">
<label for="description">Description</label><textarea id="description">Our first federated episode.</textarea>
<label for="url">Audio URL</label><input id="url" value="https://example.org/demo.mp3">
<button onclick="publish()">Publish and federate</button></section>
<section class="wide"><h2>3. Inspect HTTP activities</h2>
<small>Outbound and inbound ActivityPub messages recorded by this server.</small>
<button onclick="refresh()">Refresh protocol inspector</button>
<p id="status" role="status"></p><pre id="events">Loading…</pre></section>
</main>
<script>
const base=location.origin;
const actor=base+'/actors/podcast';
document.querySelector('#target').value=base.includes('8101')?'http://127.0.0.1:8102/actors/podcast':'http://127.0.0.1:8101/actors/podcast';
async function request(path,body){
 const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await r.json();
 if(!r.ok)throw Error(JSON.stringify(data));
 return data;
}
async function action(fn){
 try{const result=await fn();document.querySelector('#status').textContent='Success: '+JSON.stringify(result).slice(0,240)}
 catch(e){document.querySelector('#status').textContent='Error: '+e.message}
 await refresh();
}
function follow(){return action(()=>request('/follow',{actor:document.querySelector('#target').value}))}
function publish(){return action(()=>request('/episodes',{title:document.querySelector('#title').value,description:document.querySelector('#description').value,url:document.querySelector('#url').value}))}
async function refresh(){
 try{const r=await fetch('/events');document.querySelector('#events').textContent=JSON.stringify(await r.json(),null,2)}
 catch(e){document.querySelector('#events').textContent=e.message}
}
refresh();
</script></body></html>"""
    return HTMLResponse(html.replace("__TITLE__", title))
