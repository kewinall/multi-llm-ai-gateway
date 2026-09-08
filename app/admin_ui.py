# ruff: noqa: E501

from fastapi.responses import HTMLResponse


def admin_console() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Multi-LLM AI Gateway Admin</title>
<style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
body{margin:0;background:#0b1020;color:#e6edf7}
header{padding:24px 32px;border-bottom:1px solid #25304a;background:#111831;position:sticky;top:0;z-index:5}
h1{margin:0 0 8px;font-size:24px} .muted{color:#94a3b8}
main{padding:24px 32px;display:grid;gap:20px;max-width:1400px;margin:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{background:#111831;border:1px solid #25304a;border-radius:14px;padding:18px;box-shadow:0 8px 24px #0004}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
input,select,textarea,button{font:inherit;border-radius:8px;border:1px solid #334155;padding:9px 11px;background:#0f172a;color:#e6edf7}
input,textarea{flex:1;min-width:140px} button{cursor:pointer;background:#1d4ed8;border-color:#2563eb}
button.danger{background:#7f1d1d;border-color:#991b1b} button.secondary{background:#1e293b}
table{width:100%;border-collapse:collapse;font-size:14px} th,td{text-align:left;border-bottom:1px solid #25304a;padding:10px 8px;vertical-align:top}
code{color:#93c5fd}.pill{display:inline-block;border:1px solid #334155;border-radius:999px;padding:3px 8px;font-size:12px}
.ok{color:#86efac}.warn{color:#fcd34d}.keybox{word-break:break-all;background:#0b1020;padding:10px;border-radius:8px;border:1px dashed #475569}
#error{color:#fca5a5;white-space:pre-wrap}.section-title{display:flex;justify-content:space-between;align-items:center}
</style>
</head>
<body>
<header>
  <h1>Multi-LLM AI Gateway · Admin Console</h1>
  <div class="row">
    <span class="muted">Admin Key</span>
    <input id="adminKey" type="password" placeholder="X-Admin-Key">
    <button onclick="saveKey()">Connect</button>
    <span id="status" class="pill">disconnected</span>
  </div>
</header>
<main>
  <div id="error"></div>
  <section class="grid">
    <div class="card"><h3>Runtime</h3><div id="runtime">—</div></div>
    <div class="card"><h3>Usage</h3><div id="usage">—</div></div>
    <div class="card"><h3>Budget</h3><div id="budget">—</div></div>
  </section>

  <section class="card">
    <div class="section-title"><h3>Routing Policy</h3></div>
    <div class="row">
      <select id="policy"><option>priority</option><option>round_robin</option><option>random</option><option>cost</option></select>
      <button onclick="setPolicy()">Apply</button>
    </div>
  </section>

  <section class="card">
    <h3>Aliases</h3>
    <div class="row"><input id="aliasName" placeholder="default"><input id="aliasTarget" placeholder="mock:demo"><button onclick="setAlias()">Upsert</button></div>
    <div id="aliases"></div>
  </section>

  <section class="card">
    <h3>Model Pools</h3>
    <div class="row"><input id="poolName" placeholder="balanced"><input id="poolModels" placeholder="mock:a,mock:b"><button onclick="setPool()">Upsert</button></div>
    <div id="pools"></div>
  </section>

  <section class="card">
    <h3>Pricing · USD / 1M tokens</h3>
    <div class="row"><input id="priceModel" placeholder="mock:demo"><input id="priceIn" type="number" step="0.0001" placeholder="input"><input id="priceOut" type="number" step="0.0001" placeholder="output"><button onclick="setPrice()">Upsert</button></div>
    <div id="pricing"></div>
  </section>

  <section class="card">
    <h3>API Clients / RBAC</h3>
    <div class="row"><input id="clientName" placeholder="rag-app"><select id="clientRole"><option>viewer</option><option selected>operator</option><option>admin</option></select><input id="clientLimit" type="number" min="1" placeholder="RPM override"><button onclick="createClient()">Create</button></div>
    <div id="newKey"></div>
    <div id="clients"></div>
  </section>

  <section class="card">
    <h3>Audit Log</h3>
    <div id="audit"></div>
  </section>
</main>
<script>
const $=id=>document.getElementById(id);
function headers(){return {"Content-Type":"application/json","X-Admin-Key":$("adminKey").value}}
async function api(path,opts={}){
  const res=await fetch(path,{...opts,headers:{...headers(),...(opts.headers||{})}});
  if(!res.ok) throw new Error(res.status+" "+await res.text());
  const text=await res.text(); return text?JSON.parse(text):{};
}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]))}
function table(rows,cols,actions){
  if(!rows.length)return '<p class="muted">No records</p>';
  return '<table><thead><tr>'+cols.map(c=>'<th>'+c[0]+'</th>').join('')+(actions?'<th></th>':'')+'</tr></thead><tbody>'+
    rows.map(r=>'<tr>'+cols.map(c=>'<td>'+escapeHtml(c[1](r))+'</td>').join('')+(actions?'<td>'+actions(r)+'</td>':'')+'</tr>').join('')+'</tbody></table>';
}
async function refresh(){
  try{
    const [s,u,b]=await Promise.all([api('/admin/api/summary'),api('/v1/usage',{headers:{"X-API-Key":$("adminKey").value}}).catch(()=>null),api('/v1/budgets',{headers:{"X-API-Key":$("adminKey").value}}).catch(()=>null)]);
    $("status").textContent="connected";$("status").className="pill ok";$("error").textContent="";
    $("runtime").innerHTML='<b>v'+escapeHtml(s.version)+'</b><br>State: '+escapeHtml(s.governance.state_backend)+'<br>Distributed: '+escapeHtml(s.governance.governance_distributed);
    $("usage").innerHTML=u?('Requests: <b>'+u.totals.requests+'</b><br>Tokens: '+u.totals.total_tokens+'<br>Cost: $'+u.totals.cost_usd):'<span class="muted">Use an admin client API key for /v1 usage</span>';
    $("budget").innerHTML=b?('Daily: $'+b.daily.spent_usd+' / '+(b.daily.limit_usd??'∞')+'<br>Monthly: $'+b.monthly.spent_usd+' / '+(b.monthly.limit_usd??'∞')):'<span class="muted">Use an admin client API key for /v1 budgets</span>';
    $("policy").value=s.governance.routing_policy;
    const aliases=Object.entries(s.governance.aliases).map(([name,target])=>({name,target}));
    $("aliases").innerHTML=table(aliases,[["Name",r=>r.name],["Target",r=>r.target]],r=>'<button class="danger" onclick="delAlias(\''+r.name+'\')">Delete override</button>');
    const pools=Object.entries(s.governance.pools).map(([name,models])=>({name,models:models.join(', ')}));
    $("pools").innerHTML=table(pools,[["Name",r=>r.name],["Models",r=>r.models]],r=>'<button class="danger" onclick="delPool(\''+r.name+'\')">Delete override</button>');
    const prices=Object.entries(s.governance.pricing).map(([model,p])=>({model,input:p.input_per_million,output:p.output_per_million}));
    $("pricing").innerHTML=table(prices,[["Model",r=>r.model],["Input",r=>r.input],["Output",r=>r.output]],r=>'<button class="danger" onclick="delPrice(\''+r.model+'\')">Delete override</button>');
    $("clients").innerHTML=table(s.clients,[["Name",r=>r.name],["Role",r=>r.role],["Enabled",r=>r.enabled],["RPM",r=>r.rate_limit_requests_per_minute??'default']],r=>'<button class="danger" onclick="delClient(\''+r.id+'\')">Delete</button>');
    $("audit").innerHTML=table(s.audit,[["Time",r=>r.timestamp],["Actor",r=>r.actor],["Action",r=>r.action],["Resource",r=>r.resource]]);
  }catch(e){$("status").textContent="error";$("status").className="pill warn";$("error").textContent=e.message}
}
function saveKey(){sessionStorage.setItem('adminKey',$("adminKey").value);refresh()}
async function setPolicy(){await api('/admin/api/settings/routing-policy',{method:'PUT',body:JSON.stringify({routing_policy:$("policy").value})});refresh()}
async function setAlias(){await api('/admin/api/aliases/'+encodeURIComponent($("aliasName").value),{method:'PUT',body:JSON.stringify({target:$("aliasTarget").value})});refresh()}
async function delAlias(n){await api('/admin/api/aliases/'+encodeURIComponent(n),{method:'DELETE'});refresh()}
async function setPool(){await api('/admin/api/pools/'+encodeURIComponent($("poolName").value),{method:'PUT',body:JSON.stringify({models:$("poolModels").value.split(',').map(x=>x.trim()).filter(Boolean)})});refresh()}
async function delPool(n){await api('/admin/api/pools/'+encodeURIComponent(n),{method:'DELETE'});refresh()}
async function setPrice(){await api('/admin/api/pricing/'+encodeURIComponent($("priceModel").value),{method:'PUT',body:JSON.stringify({input_per_million:Number($("priceIn").value),output_per_million:Number($("priceOut").value)})});refresh()}
async function delPrice(n){await api('/admin/api/pricing/'+encodeURIComponent(n),{method:'DELETE'});refresh()}
async function createClient(){
  const rpm=$("clientLimit").value;
  const out=await api('/admin/api/clients',{method:'POST',body:JSON.stringify({name:$("clientName").value,role:$("clientRole").value,rate_limit_requests_per_minute:rpm?Number(rpm):null})});
  $("newKey").innerHTML='<p class="warn">Copy this key now. It is shown only once.</p><div class="keybox">'+escapeHtml(out.api_key)+'</div>';refresh()
}
async function delClient(id){await api('/admin/api/clients/'+id,{method:'DELETE'});refresh()}
$("adminKey").value=sessionStorage.getItem('adminKey')||'';
if($("adminKey").value)refresh();
</script>
</body>
</html>"""
    )
