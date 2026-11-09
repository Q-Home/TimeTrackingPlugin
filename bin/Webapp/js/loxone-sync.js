/* Credentials and Miniserver commands never enter this browser. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fields=Array.from({length:5},(_,i)=>'customField'+(i+1));
  const metrics={none:'Niet gebruiken',today:'Vandaag gewerkt',week:'Deze week gewerkt',month:'Deze maand gewerkt',balance:'Urensaldo (maand tot vandaag)',status:'Registratiestatus',updated:'Laatst bijgewerkt'};
  const state={config:null,probe:null,rows:[],users:[],employee:null};
  const when=v=>v?new Date(v).toLocaleString('nl-BE'):'Nog niet';
  function notice(message,error=false){$('feedback').innerHTML=`<div class="notice ${error?'error':''}">${esc(message)}</div>`;}
  async function api(path,options={}){
    const response=await fetch('/api/v1/loxone-sync'+path,{cache:'no-store',...options,headers:{Authorization:'Bearer '+(localStorage.getItem('access_token')||''),...options.headers}});
    if(response.status===401){location.href='index.html';throw Error('Meld opnieuw aan.');}
    const body=await response.json();if(!response.ok)throw Error(body.error||'De aanvraag kon niet worden verwerkt.');return body.data;
  }
  const post=(path,data={})=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const fail=e=>notice(e.message,true);
  async function busy(button,action){button.disabled=true;try{await action();}catch(e){fail(e);}finally{button.disabled=false;}}
  function renderMapping(){
    const mapping=state.config.mapping;
    $('mapping').innerHTML=fields.map(f=>`<div class="field-map"><div><strong>${esc(state.probe?.field_names[f]||f)}</strong><small>${f} · veldnaam wordt niet gewijzigd</small></div><label>Te synchroniseren<select data-field="${f}">${Object.entries(metrics).map(([key,label])=>`<option value="${key}" ${mapping[f]===key?'selected':''}>${label}</option>`).join('')}</select></label></div>`).join('');
    $('interval').value=state.config.interval;$('enabled').checked=state.config.enabled;$('ownership').checked=false;
    $('enabled-label').textContent=state.config.enabled?'Ingeschakeld':'Uitgeschakeld';
  }
  function renderRows(data){
    state.rows=data.rows;
    $('queue').innerHTML=`<p class="muted">Laatste taak: ${esc(when(data.run.at))}${data.run.at?` · ${data.run.success||0} gecontroleerd · ${data.run.writes||0} bijgewerkt · ${data.run.failed||0} fouten`:''}. ${data.pending.sequence> (data.run.sequence||0)?'Een nieuwe ronde staat ingepland.':''}</p>`;
    $('employees').innerHTML=state.rows.length?state.rows.map(row=>`<article class="sync-person"><div class="section-head"><div><h3>${esc(row.employee.name)}</h3><span class="muted">Tijdregistratie: ${esc(row.employee.username)}</span></div><button class="secondary" data-link="${esc(row.employee.id)}">${row.binding?'Koppeling bekijken / vervangen':'Gebruiker koppelen'}</button></div>
      <div class="sync-meta"><span class="badge ${row.binding?'neutral':'warning'}">${esc(row.link_status)}</span><span>Loxone: ${esc(row.remote?.name||row.binding?.name||'Niet gekoppeld')}</span></div>${row.binding?`<code>UUID ${esc(row.binding.uuid)} · Miniserver ${esc(row.binding.server.serial)}</code>`:''}
      <p class="muted">Laatste geslaagde controle: ${esc(when(row.last_success))} · Inhoudelijk bijgewerkt: ${esc(when(row.last_content_update))}</p>
      ${row.last_error?`<div class="notice error">${esc(row.last_error)}${row.retry_at?` Volgende poging vanaf ${esc(when(row.retry_at))}.`:''}</div>`:''}
      <div class="sync-values">${['today','week','month','balance','status'].map(m=>`<div class="sync-value"><small>${metrics[m]}</small><strong>${esc(row.values[m]||'Niet beschikbaar')}</strong></div>`).join('')}</div>
      ${row.remote?`<div class="sync-current"><strong>Bestaande waarden in Loxone</strong><br>${fields.map(f=>`${esc(state.probe?.field_names[f]||f)}: ${esc(row.remote.fields[f]||'(leeg)')}`).join(' · ')}</div>`:'<p class="muted">Dry-run leest de bestaande custom fields; er wordt niets geschreven.</p>'}
      ${row.changes?`<p><strong>Voorgenomen wijzigingen:</strong> ${Object.entries(row.changes).map(([f,v])=>`${esc(state.probe?.field_names[f]||f)} → ${esc(v)}`).join(' · ')||'Geen inhoudelijke wijziging nodig.'}</p>`:''}
      ${Object.keys(row.issues).length?`<details><summary>Waarom zijn gegevens niet beschikbaar?</summary><ul>${Object.entries(row.issues).map(([m,issues])=>`<li>${metrics[m]}: ${esc(issues.join(' '))}</li>`).join('')}</ul></details>`:''}</article>`).join(''):'<div class="empty">Nog geen medewerkers om te koppelen. Maak medewerkers aan in Accounts & rechten.</div>';
    document.querySelectorAll('[data-link]').forEach(b=>b.onclick=()=>busy(b,()=>openLink(b.dataset.link)));
  }
  async function reload(){state.config=await api('/config');renderMapping();renderRows(await api('/diagnostics'));}
  async function testConnection(){
    if(!$('server').value)throw Error('Selecteer een Miniserver.');
    state.probe=await post('/test',{slot:$('server').value});
    $('probe').innerHTML=`<div class="note">Verbinding geslaagd · LoxBerry ${esc(state.probe.loxberry_version)} · Miniserver ${esc(state.probe.miniserver_version)} · Identiteit ${esc(state.probe.server.serial)} · ${state.probe.user_count} zichtbare gebruikers.</div>`;
    renderMapping();notice('Verbinding en leesrechten gecontroleerd. Schrijfrechten worden pas bij een expliciet ingeschakelde update gecontroleerd.');
  }
  async function openLink(uid){
    state.employee=uid;$('link-form').reset();$('link-error').classList.add('hidden');
    state.users=await api('/users');
    const row=state.rows.find(r=>r.employee.id===uid);$('link-person').textContent=row.employee.name+' · '+row.employee.username;
    $('remote-users').innerHTML='<option value="">Exact op gebruikersnaam zoeken</option>'+state.users.map(u=>`<option value="${esc(u.uuid)}">${esc(u.name)} · ${esc(u.uuid)}</option>`).join('');
    if(row.binding)$('link-form').elements.loxone_username.value=row.binding.lookup_name||'';
    $('link-dialog').showModal();
  }
  async function init(){
    const response=await fetch('/api/v1/hr/me',{headers:{Authorization:'Bearer '+(localStorage.getItem('access_token')||'')}});
    if(response.status===401){location.href='index.html';return;}
    const me=(await response.json()).data;if(!me?.can_technical){$('settings').innerHTML='<div class="panel">Je hebt geen rechten voor deze koppeling.</div>';$('diagnostics').remove();return;}
    $('identity').textContent=me.username+' · Technisch beheer';
    $('logout').onclick=()=>{localStorage.clear();location.href='index.html';};
    $('settings-tab').onclick=()=>{$('settings').classList.remove('hidden');$('diagnostics').classList.add('hidden');};
    $('diagnostics-tab').onclick=()=>{$('settings').classList.add('hidden');$('diagnostics').classList.remove('hidden');};
    $('refresh').onclick=()=>busy($('refresh'),reload);
    $('test').onclick=()=>busy($('test'),testConnection);
    $('server').onchange=()=>{state.probe=null;$('probe').textContent='Test de nieuwe selectie vóór opslaan.';};
    $('preview').onclick=()=>busy($('preview'),async()=>{renderRows(await post('/preview'));notice('Dry-run afgerond: geen velden geschreven. De preview gebruikt de opgeslagen veldmapping.');});
    $('run').onclick=()=>busy($('run'),async()=>{const result=await post('/run');notice(result.message);renderRows(await api('/diagnostics'));});
    $('config-form').onsubmit=event=>{event.preventDefault();busy(event.submitter,async()=>{
      const mapping=Object.fromEntries([...document.querySelectorAll('[data-field]')].map(el=>[el.dataset.field,el.value]));
      const slot=$('server').value;
      const server=state.probe?.server.slot===slot?state.probe.server:state.config.server?.slot===slot?state.config.server:null;
      if(slot&&!server)throw Error('Test eerst de geselecteerde Miniserver.');
      const owned_fields=$('ownership').checked?fields.filter(f=>mapping[f]!=='none'):[];
      await post('/config',{revision:state.config.revision,enabled:$('enabled').checked,server,mapping,interval:Number($('interval').value),owned_fields,reason:$('reason').value});
      await reload();notice('Instellingen opgeslagen. Synchronisatie schrijft alleen wanneer ze expliciet ingeschakeld is.');
    });};
    $('cancel-link').onclick=()=>$('link-dialog').close();
    $('link-form').onsubmit=async event=>{
      event.preventDefault();const button=event.submitter;button.disabled=true;
      try{const form=new FormData(event.target);await post('/links',{revision:state.config.revision,employee_id:state.employee,loxone_username:form.get('loxone_username'),uuid:form.get('uuid'),replace:form.has('replace'),reason:form.get('reason')});$('link-dialog').close();await reload();notice('UUID-koppeling opgeslagen. Er zijn nog geen custom fields geschreven.');}
      catch(e){$('link-error').textContent=e.message;$('link-error').classList.remove('hidden');}finally{button.disabled=false;}
    };
    await reload();
    try{const inventory=await api('/miniservers');$('server').innerHTML='<option value="">Selecteer een Miniserver</option>'+inventory.servers.map(s=>`<option value="${esc(s.slot)}">${esc(s.name)} · ${esc(s.slot)}</option>`).join('');$('server').value=state.config.server?.slot||'';$('connection').textContent='LoxBerry '+inventory.loxberry_version+' · '+inventory.servers.length+' geconfigureerde Miniservers.';}
    catch(e){$('connection').textContent=e.message;}
  }
  document.addEventListener('DOMContentLoaded',()=>init().catch(fail));
})();
