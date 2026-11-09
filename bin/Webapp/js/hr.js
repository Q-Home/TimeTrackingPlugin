/* HR screens share one backend model; no fixed daily norm is calculated here. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {me:null,employees:[],config:null,revision:0,page:1,view:new URLSearchParams(location.search).get('view')||'hours',tab:'schedules',detail:null};
  const nonce = () => typeof crypto.randomUUID==='function' ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('');
  const labels = {geen_registratie:'Geen registratie',bezig:'Bezig',afgesloten:'Afgesloten',afwijking:'Afwijking',goedgekeurd:'Goedgekeurd',te_controleren:'Nog te controleren',bron_gewijzigd:'Bron gewijzigd',physical:'Fysieke registratie',manual:'Handmatige correctie',automatic:'Automatisch gegenereerd',working:'Ingeklokt',on_break:'In pauze',approved:'Goedgekeurd',closed:'Afgesloten',reopened:'Heropend',invalidated:'Goedkeuring ingetrokken'};
  const badge = value => `<span class="badge ${['afwijking','bron_gewijzigd'].includes(value)?'bad':['goedgekeurd','approved','closed'].includes(value)?'good':['bezig','te_controleren','automatic'].includes(value)?'warning':'neutral'}">${esc(labels[value]||value)}</span>`;
  const duration = seconds => seconds === null || seconds === undefined ? 'Geen rooster ingesteld' : `${seconds<0?'−':''}${Math.floor(Math.abs(seconds)/3600).toString().padStart(2,'0')}:${Math.floor(Math.abs(seconds)%3600/60).toString().padStart(2,'0')}`;
  const dateISO = date => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const timezone = () => state.config?.rules.timezone || state.me?.timezone || 'Europe/Brussels';
  const when = value => new Date(value).toLocaleString('nl-BE',{timeZone:timezone(),day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
  function localValue(value) {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:timezone(),year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value)).map(x=>[x.type,x.value]));
    return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
  }
  function notice(message,error=false) { $('feedback').innerHTML=`<div class="notice ${error?'error':''}">${esc(message)}</div>`; }
  async function api(path,options={}) {
    const response = await fetch('/api/v1/hr'+path,{cache:'no-store',...options,headers:{Authorization:`Bearer ${localStorage.getItem('access_token')||''}`,...options.headers}});
    if(response.status===401){localStorage.removeItem('access_token');location.href='index.html';throw Error('Meld opnieuw aan.');}
    const json=await response.json();
    if(!response.ok)throw Error(json.error||'De aanvraag kon niet worden verwerkt.');
    if(json.data?.revision!==undefined)state.revision=json.data.revision;
    return json.data;
  }
  async function mutate(path,data) {
    return api(path,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':nonce()},body:JSON.stringify({revision:state.revision,...data})});
  }
  function filters() {
    return new URLSearchParams({start:$('start').value,end:$('end').value,as_of:$('as-of').value,
      employee_id:state.me.can_hr?$('employee-filter').value:state.me.id,department:$('department-filter').value,status:$('status-filter').value});
  }
  function employeeOptions(all=false) {return (all?'<option value="">Iedereen</option>':'')+state.employees.filter(e=>!e.unresolved).map(e=>`<option value="${esc(e.id)}">${esc(e.name)}</option>`).join('');}
  const reasonField = '<label class="wide">Reden (verplicht)<textarea name="reason" required minlength="3" maxlength="2000" placeholder="Waarom is deze wijziging nodig?"></textarea></label>';
  function modal(title,fields,submit,label='Opslaan') {
    $('modal-title').textContent=title;$('modal-fields').innerHTML=fields;$('modal-submit').textContent=label;
    $('modal-error')?.remove();
    $('modal-form').onsubmit=async event=>{
      event.preventDefault();$('modal-submit').disabled=true;
      try{await submit(new FormData(event.target));$('modal').close();notice('De wijziging is opgeslagen.');await reload();}
      catch(error){notice(error.message,true);$('modal-error')?.remove();const message=document.createElement('p');message.id='modal-error';message.className='notice error';message.textContent=error.message;$('modal-fields').prepend(message);}
      finally{$('modal-submit').disabled=false;}
    };
    $('modal').showModal();
  }
  const table = (headers,rows) => `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  function stat(label,value,small='',alert=false){return `<div class="stat ${alert?'alert':''}"><p>${label}</p><span class="value">${value}</span><small>${small}</small></div>`;}
  function configureNavigation() {
    const items=state.me.can_hr?[['dashboard','Overzicht'],['hours','Urenoverzicht'],['review','Te controleren'],['settings','HR-instellingen']]:[['hours','Mijn uren']];
    $('navigation').innerHTML=items.map(([view,name])=>`<a href="hr.html?view=${view}" data-view="${view}" class="${state.view===view?'active':''}">${name}</a>`).join('')+(state.me.can_technical?'<a href="logs.html">Diagnose & koppelingen</a><a href="settings.html">Branding & technisch beheer</a><a href="user-list.html">Accounts & rechten</a>':'');
    $('identity').textContent=`${state.me.username} · ${state.me.role==='hr'?'HR':state.me.role==='technical_admin'?'Technisch beheer':state.me.role==='admin'?'Beheerder':'Medewerker'}`;
    document.querySelectorAll('.hr-only').forEach(e=>e.classList.toggle('hidden',!state.me.can_hr));
    if(!state.me.can_hr && state.me.role==='technical_admin'){
      state.view='technical';$('filters').classList.add('hidden');
    }
  }
  async function loadConfig() {if(state.me.can_hr){state.config=await api('/config');}}
  async function reload() {
    $('feedback').querySelector('.notice.error')?.remove();
    if(state.me.can_hr){state.employees=await api('/employees');await loadConfig();}
    const names={dashboard:'Vandaag & opvolging',hours:state.me.can_hr?'Urenoverzicht':'Mijn uren',review:'Te controleren',settings:'HR-instellingen',technical:'Technisch beheer'};
    $('page-title').textContent=names[state.view]||names.hours;
    $('page-description').textContent=state.view==='settings'?'Roosters, kalender en regels met een expliciete ingangsdatum.':'Betrouwbare dagdetails, duidelijke afwijkingen en controleerbare correcties.';
    $('filters').classList.toggle('hidden',['settings','dashboard','technical'].includes(state.view));
    if(state.view==='dashboard')await dashboard();
    else if(state.view==='settings')settings();
    else if(state.view==='review')await review();
    else if(state.view==='technical')await technical();
    else if(state.detail)await detail(state.detail);
    else if(!state.me.can_hr)await detail(state.me.id);
    else await overview();
  }
  async function overview() {
    const query=filters();query.set('page',state.page);query.set('limit','25');const data=await api('/overview?'+query);
    const totals=data.totals;
    $('content').innerHTML=`<div class="stats">${stat('Geregistreerd netto',duration(totals.work_seconds),'Alle gefilterde medewerkers')}${stat('Verwacht t/m peildatum',totals.expected_seconds===null?'—':duration(totals.expected_seconds),'Toekomstige dagen niet meegerekend')}${stat('Urensaldo',totals.balance_seconds===null?'—':duration(totals.balance_seconds),'Geen automatische betaalde overuren')}${stat('Afwijkingen',totals.anomaly_count,'Te beoordelen',true)}${stat('Medewerkers',data.total,'Binnen de gekozen filters')}</div>
    <div class="panel"><div class="section-head"><h2>Medewerkers & uren</h2><button id="export">Alle resultaten exporteren</button></div><p class="muted">De periodenorm staat apart onder de norm t/m peildatum. Lopende uren zijn voorlopig.</p>
    ${data.rows.length?table(['Medewerker','Afdeling','Norm / volledige periode','Netto','Pauze','Urensaldo','Controle','Goedkeuring'],data.rows.map(r=>`<tr><td><button class="text-button" data-open="${esc(r.employee.id)}"><strong>${esc(r.employee.name)}</strong></button><small>${esc(r.employee.personnel_number||r.employee.username)}${r.employee.unresolved?' · identiteit koppelen':''}</small></td><td>${esc(r.employee.department||'—')}</td><td>${duration(r.expected_seconds)}<small>Volledige periode: ${duration(r.full_expected_seconds)}</small></td><td><strong>${duration(r.work_seconds)}</strong>${r.provisional?'<small>Voorlopig</small>':''}</td><td>${duration(r.break_seconds)}</td><td class="balance">${duration(r.balance_seconds)}</td><td>${badge(r.control_status)}<small>${r.anomaly_count} afwijkingen</small></td><td>${badge(r.approval_status)}</td></tr>`)):'<div class="empty">Geen medewerkers voor deze filters. Pas de periode of afdeling aan.</div>'}
    <div class="pager"><span>${data.total} medewerkers · pagina ${state.page}</span><button class="secondary" id="previous" ${state.page===1?'disabled':''}>Vorige</button><button class="secondary" id="next" ${state.page*25>=data.total?'disabled':''}>Volgende</button></div></div>`;
    bindOpen();$('export').onclick=download;
    $('previous').onclick=()=>{state.page--;overview().catch(fail);};$('next').onclick=()=>{state.page++;overview().catch(fail);};
  }
  async function detail(uid) {
    state.view='hours';$('filters').classList.remove('hidden');$('page-title').textContent=state.me.can_hr?'Urenoverzicht':'Mijn uren';configureNavigation();
    state.detail=uid;const data=await api('/details/'+encodeURIComponent(uid)+'?'+filters());const summary=data.summary;
    const existing=data.approvals.filter(a=>a.status==='approved'||a.status==='closed');
    const exact=existing.find(a=>a.start===data.start&&a.end===data.end);
    $('content').innerHTML=`<div class="section-head"><div><h2>${esc(data.employee.name)}</h2><p class="muted">${esc(data.employee.personnel_number||'Geen personeelsnummer')} · ${esc(data.employee.department||'Geen afdeling')} · Tijden: ${esc(timezone())}</p></div><div>${state.me.can_hr?'<button class="secondary" id="back">Alle medewerkers</button> ':''}<button id="export">CSV-export</button></div></div>
    <div class="stats">${stat('Netto',duration(summary.work_seconds),summary.provisional?'Bevat voorlopige uren':'Gesloten werkperiodes')}${stat('Verwacht t/m peildatum',summary.expected_seconds===null?'—':duration(summary.expected_seconds),summary.schedule_missing?'Geen rooster ingesteld':'Volledige periode: '+duration(summary.full_expected_seconds))}${stat('Urensaldo',summary.balance_seconds===null?'—':duration(summary.balance_seconds),'Verschil met rooster')}${stat('Pauze',duration(summary.break_seconds))}${stat('Afwijkingen',summary.anomaly_count,'Controleer de dagdetails',true)}</div>
    <div class="panel"><div class="section-head"><h2>Dagdetails</h2><div>${state.me.can_hr?'<button id="add-event">Registratie aanvullen</button> <button class="secondary" id="approve">Goedkeuren</button> '+(exact?`<button class="secondary" id="period-action">${exact.status==='closed'?'Heropenen':'Afsluiten'}</button>${exact.status==='approved'?'<button class="secondary" id="invalidate">Goedkeuring intrekken</button>':''}`:''):'<button id="request-add">Correctie aanvragen</button>'}</div></div>
    ${data.employee.unresolved?'<div class="note warning">Deze historische identiteit is nog niet gekoppeld. <button id="link-identity" class="secondary">Koppelen aan medewerker</button></div>':''}
    ${existing.length?`<p class="muted">Bestaande perioden: ${existing.map(a=>`<button class="text-button" data-period="${esc(a.id)}">${esc(a.start)} — ${esc(a.end)} (${labels[a.status]})</button>`).join('')}</p>`:''}
    ${data.days.map(d=>`<details class="day" ${d.anomalies.length?'open':''}><summary><span><strong>${esc(new Date(d.date+'T12:00:00').toLocaleDateString('nl-BE',{weekday:'long',day:'numeric',month:'long'}))}</strong><small>Eerste start: ${first(d,'START')} · Laatste stop: ${last(d,'STOP')}</small></span><span>Norm ${duration(d.expected_seconds)} · Netto <strong>${duration(d.work_seconds)}</strong> ${badge(d.status)} ${badge(d.approval_status)}</span></summary><div>
    ${d.anomalies.length?`<ul class="error-list">${d.anomalies.map(a=>`<li>${esc(a.message)}</li>`).join('')}</ul>`:''}
    <div class="periods">${d.periods.map(p=>`<span class="period ${p.kind==='break'?'break':''}">${p.kind==='break'?'Pauze':'Werk'} ${when(p.start)} → ${when(p.end)} · ${duration(p.seconds)}${p.provisional?' · voorlopig':''}</span>`).join('')}${d.automatic_break_seconds?`<span class="period break">Automatische pauzeaftrek ${duration(d.automatic_break_seconds)} (geen geregistreerde pauze)</span>`:''}</div>
    ${d.events.length?table(['Tijdstip','Actie','Laatste registratiepunt','Herkomst',''],d.events.map(e=>`<tr><td>${esc(when(e.timestamp))}</td><td>${esc(e.action)}</td><td>${esc(e.location||e.device_id||'—')}</td><td>${badge(e.source)}</td><td><button class="text-button" data-event="${esc(e.id)}">${state.me.can_hr?'Corrigeren / controleren':'Correctie aanvragen'}</button></td></tr>`)):'<p class="muted">Geen registraties op deze dag.</p>'}</div></details>`).join('')}
    </div><div class="panel"><h2>Correctieaanvragen & audit</h2>${data.requests.length?table(['Reden','Status','Aangevraagd'],data.requests.map(r=>`<tr><td>${esc(r.reason)}</td><td>${esc(r.status)}</td><td>${esc(when(r.at))}</td></tr>`)):'<p class="muted">Er zijn nog geen correctieaanvragen.</p>'}<details><summary>Wijzigingshistoriek (${data.audit.length})</summary><pre class="audit">${esc(JSON.stringify(data.audit,null,2))}</pre></details></div>`;
    $('back')?.addEventListener('click',()=>{state.detail=null;reload().catch(fail);});$('export').onclick=download;
    const events=data.days.flatMap(d=>d.events);
    document.querySelectorAll('[data-event]').forEach(b=>b.onclick=()=>correction(uid,events.find(e=>e.id===b.dataset.event)));
    $('add-event')?.addEventListener('click',()=>correction(uid));$('request-add')?.addEventListener('click',()=>correction(uid));
    $('approve')?.addEventListener('click',()=>periodAction(uid,'approve',data.start,data.end));
    $('invalidate')?.addEventListener('click',()=>periodAction(uid,'invalidate',exact.start,exact.end));
    $('period-action')?.addEventListener('click',()=>periodAction(uid,exact.status==='closed'?'reopen':'close',exact.start,exact.end));
    document.querySelectorAll('[data-period]').forEach(b=>b.onclick=()=>{const a=existing.find(x=>x.id===b.dataset.period);$('start').value=a.start;$('end').value=a.end;reload().catch(fail);});
    $('link-identity')?.addEventListener('click',()=>modal('Historische identiteit koppelen',`<label>Medewerker<select name="employee_id">${employeeOptions()}</select></label>${reasonField}`,f=>mutate('/config/identity',{employee_id:f.get('employee_id'),identity_key:data.employee.identity_key,reason:f.get('reason')})));
  }
  const first=(d,action)=>{const event=d.events.find(e=>e.action===action);return event?esc(when(event.timestamp)):'—';};
  const last=(d,action)=>{const event=[...d.events].reverse().find(e=>e.action===action);return event?esc(when(event.timestamp)):'—';};
  function correction(uid,event=null,requestRecord=null,proposal=null) {
    const source=requestRecord?.proposed||proposal?.new||event||{};
    const value=source.local_time||(source.timestamp?localValue(source.timestamp):$('start').value+'T09:00');
    modal(state.me.can_hr?'Registratie corrigeren / aanvullen':'Correctie aanvragen',`<div class="note">Het oorspronkelijke event blijft bewaard. Tijden zijn in ${esc(timezone())}.</div><div class="form-grid"><label>Actie<select name="action">${['START','BREAK','RETURN','STOP'].map(a=>`<option ${a===source.action?'selected':''}>${a}</option>`).join('')}</select></label><label>Datum en tijd<input type="datetime-local" name="local_time" value="${esc(value)}" required></label><label>Bij dubbel winteruur<select name="fold"><option value="">Automatisch / niet van toepassing</option><option value="0">Eerste uur (zomertijd)</option><option value="1">Tweede uur (wintertijd)</option></select></label>${state.me.can_hr&&(event||requestRecord?.target_id)?'<label class="check"><input type="checkbox" name="void">Registratie laten vervallen</label>':''}${state.me.can_hr?'<label class="check wide"><input type="checkbox" name="invalidate">Bestaande goedkeuring expliciet intrekken</label>':''}${reasonField}</div>`,async f=>{
      const next={action:f.get('action'),local_time:f.get('local_time')};if(f.get('fold')!=='')next.fold=Number(f.get('fold'));
      const base={employee_id:uid,target_id:event?.id||requestRecord?.target_id,reason:f.get('reason')};
      if(state.me.can_hr)await mutate('/corrections',{...base,new:f.has('void')?null:next,invalidate_approval:f.has('invalidate'),request_id:requestRecord?.id,proposal_id:proposal?.id});
      else await mutate('/requests',{...base,proposed:next});
    },state.me.can_hr?'Correctie vastleggen':'Aanvraag versturen');
  }
  function periodAction(uid,action,start,end) {
    modal({approve:'Periode goedkeuren',close:'Periode afsluiten',reopen:'Periode heropenen',invalidate:'Goedkeuring intrekken'}[action],`<p>${esc(start)} t/m ${esc(end)}</p><p class="muted">Afgesloten uren kunnen alleen na heropening worden gewijzigd.</p>${reasonField}`,f=>mutate('/approvals',{employee_id:uid,start,end,action,reason:f.get('reason')}));
  }
  function bindOpen(){document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>detail(b.dataset.open).catch(fail));}
  async function download() {
    const query=filters();if(state.detail)query.set('employee_id',state.detail);
    const response=await fetch('/api/v1/hr/export?'+query,{headers:{Authorization:`Bearer ${localStorage.getItem('access_token')}`}});
    if(!response.ok){fail(Error('De export is niet gelukt.'));return;}
    const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='urenoverzicht.csv';a.click();URL.revokeObjectURL(url);
  }
  async function review() {
    const data=await api('/worklist?'+filters());
    const requests=[...data.requests.map(r=>({...r,kind:'request'})),...data.proposals.map(p=>({...p,kind:'proposal'}))];
    $('content').innerHTML=`<div class="panel"><div class="section-head"><h2>Afwijkingen per medewerkerdag</h2><span class="badge warning">${data.rows.length} dagen te controleren</span></div>${data.rows.length?table(['Medewerker','Datum','Afwijkingen',''],data.rows.map(r=>`<tr><td>${esc(r.employee.name)}</td><td>${esc(r.day.date)}</td><td>${r.day.anomalies.map(a=>esc(a.message)).join('<br>')}</td><td><button data-open="${esc(r.employee.id)}">Dagdetails</button></td></tr>`)):'<div class="empty">Geen afwijkingen in de gekozen periode.</div>'}</div>
    <div class="panel"><h2>Correctieaanvragen & voorgestelde eindtijden</h2>${requests.length?table(['Medewerker','Aanvraag','Voorstel',''],requests.map(r=>`<tr><td>${esc(state.employees.find(e=>e.id===r.employee_id)?.name||r.employee_id)}</td><td>${esc(r.reason||'Voorgestelde automatische STOP')}</td><td>${esc(JSON.stringify(r.proposed||r.new))}</td><td><button data-review="${esc(r.id)}">Behandelen</button> <button class="secondary" data-reject="${esc(r.id)}">Afwijzen</button></td></tr>`)):'<div class="empty">Geen open correctieaanvragen of voorstellen.</div>'}</div>`;
    bindOpen();document.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>{const r=requests.find(r=>r.id===b.dataset.review);correction(r.employee_id,null,r.kind==='request'?r:null,r.kind==='proposal'?r:null);});
    document.querySelectorAll('[data-reject]').forEach(b=>b.onclick=()=>{const r=requests.find(r=>r.id===b.dataset.reject);modal('Aanvraag afwijzen',reasonField,f=>mutate('/requests/reject',{[r.kind==='proposal'?'proposal_id':'request_id']:r.id,reason:f.get('reason')}));});
  }
  async function dashboard() {
    const data=await api('/dashboard');
    $('content').innerHTML=`<div class="stats">${stat('Ingeklokt',data.clocked_in,'Afgeleid uit registraties')}${stat('In pauze',data.on_break)}${stat('Afwijkingen',data.anomalies,'Laatste 30 dagen',true)}${stat('Automatisch afgesloten',data.automatic_to_review,'Nog te controleren',true)}${stat('Nog goed te keuren',data.pending_approval,'Medewerkers met open controle')}</div>
    ${data.notifications_enabled&&data.anomalies?'<div class="note warning">Er zijn registraties die aandacht vragen. Open Te controleren om ze te behandelen.</div>':''}
    <div class="panel"><div class="section-head"><h2>Huidige registratiestatus</h2><a href="hr.html?view=review">Naar Te controleren →</a></div><p class="muted">Het laatste registratiepunt bewijst geen actuele fysieke locatie.</p>${data.people.length?table(['Medewerker','Status','Laatste registratiepunt'],data.people.map(p=>`<tr><td><button class="text-button" data-open="${esc(p.employee.id)}">${esc(p.employee.name)}</button></td><td>${badge(p.status)}</td><td>${esc(p.last_registration_point)}</td></tr>`)):'<div class="empty">Op dit moment zijn geen open sessies bekend.</div>'}</div>`;
    bindOpen();
  }
  function settings() {
    const tabs=[['schedules','Werkroosters'],['calendar','Kalender & afwezigheid'],['rules','Pauzes, registratie & urensaldo'],['approval','Goedkeuring & export'],['people','Medewerkers'],['roles','Rollen & rechten']];
    $('content').innerHTML=`<div class="tabs">${tabs.map(([id,name])=>`<button data-tab="${id}" class="${state.tab===id?'active':''}">${name}</button>`).join('')}</div><div id="settings-body"></div>`;
    document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;settings();});
    if(state.tab==='schedules')scheduleSettings();else if(state.tab==='calendar')calendarSettings();else if(state.tab==='people')peopleSettings();else if(state.tab==='roles')roleSettings();else ruleSettings();
  }
  function settingsForm(id,submit) {
    $(id).onsubmit=async e=>{e.preventDefault();try{await submit(new FormData(e.target));notice('Instelling opgeslagen met wijzigingshistoriek.');await reload();}catch(error){fail(error);}};
  }
  function scheduleSettings() {
    const days=['Maandag','Dinsdag','Woensdag','Donderdag','Vrijdag','Zaterdag','Zondag'];const cfg=state.config;
    $('settings-body').innerHTML=`<div class="grid2"><form id="schedule-form" class="panel"><h2>Herbruikbaar rooster maken</h2><p class="muted">Netto-uren zijn de norm na pauzes. Bestaande roosters blijven als historische versie bewaard.</p><label>Naam<input name="name" required placeholder="Bijvoorbeeld: deeltijds 24 uur"></label>${table(['Weekdag','Netto-uren','Begin (optioneel)','Einde (optioneel)'],days.map((d,i)=>`<tr><td>${d}</td><td><input type="number" name="hours${i}" min="0" max="24" step="0.25" value="0" aria-label="Netto-uren ${d}"></td><td><input type="time" name="start${i}" aria-label="Begin ${d}"></td><td><input type="time" name="end${i}" aria-label="Einde ${d}"></td></tr>`))}${reasonField}<button>Rooster opslaan</button></form>
    <div><form id="assignment-form" class="panel"><h2>Rooster toewijzen</h2><div class="form-grid"><label>Medewerker<select name="employee_id">${employeeOptions()}</select></label><label>Rooster<select name="schedule_id">${cfg.schedules.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('')}</select></label><label>Ingangsdatum<input type="date" name="effective_from" value="${dateISO(new Date())}" required></label>${reasonField}</div><button ${cfg.schedules.length?'':'disabled'}>Toewijzen met ingangsdatum</button></form><div class="panel"><h2>Toewijzingshistoriek</h2>${cfg.assignments.length?table(['Medewerker','Rooster','Vanaf'],cfg.assignments.map(a=>`<tr><td>${esc(state.employees.find(e=>e.id===a.employee_id)?.name||a.employee_id)}</td><td>${esc(cfg.schedules.find(s=>s.id===a.schedule_id)?.name)}</td><td>${esc(a.effective_from)}</td></tr>`)):'<p class="muted">Nog geen roosters toegewezen. Er wordt geen fictieve dag- of weeknorm toegepast.</p>'}</div></div></div>`;
    settingsForm('schedule-form',f=>mutate('/config/schedule',{schedule:{name:f.get('name'),days:days.map((_,i)=>({minutes:Number(f.get('hours'+i))*60,start:f.get('start'+i),end:f.get('end'+i)}))},reason:f.get('reason')}));
    settingsForm('assignment-form',f=>mutate('/config/assignment',Object.fromEntries(f)));
  }
  function calendarSettings() {
    $('settings-body').innerHTML=`<div class="grid2"><form id="calendar-form" class="panel"><h2>Feestdag, sluiting of afwezigheid</h2><div class="form-grid"><label>Soort<select name="kind"><option value="holiday">Feestdag</option><option value="closure">Bedrijfssluiting</option><option value="absence">Individuele afwezigheid</option></select></label><label>Omschrijving<input name="label" required></label><label>Vanaf<input type="date" name="start" required></label><label>Tot en met<input type="date" name="end" required></label><label>Medewerker<select name="employee_id">${employeeOptions(true)}</select></label><label>Afdeling (optioneel)<input name="department"></label><label>Invloed op norm<select name="effect"><option value="zero">Norm wordt nul</option><option value="keep">Norm blijft behouden</option><option value="hours">Aangepaste netto-uren</option></select></label><label>Aangepaste netto-uren<input type="number" name="hours" value="0" min="0" max="24" step="0.25"></label>${reasonField}</div><button>Kalenderregel vastleggen</button></form><div class="panel"><h2>Kalenderregels</h2>${state.config.calendar.length?table(['Periode','Omschrijving','Invloed',''],state.config.calendar.map(c=>`<tr><td>${esc(c.start)}<small>t/m ${esc(c.end)}</small></td><td>${esc(c.label)}<small>${esc(state.employees.find(e=>e.id===c.employee_id)?.name||c.department||'Iedereen')}</small></td><td>${esc({zero:'Norm nul',keep:'Norm behouden',hours:c.minutes/60+' uur'}[c.effect])}</td><td><button type="button" class="secondary" data-calendar="${esc(c.id)}">Intrekken</button></td></tr>`)):'<div class="empty">Nog geen kalenderregels ingesteld.</div>'}</div></div>`;
    settingsForm('calendar-form',f=>mutate('/config/calendar',{...Object.fromEntries(f),employee_id:f.get('employee_id')||null,minutes:Number(f.get('hours'))*60}));
    document.querySelectorAll('[data-calendar]').forEach(b=>b.onclick=()=>modal('Kalenderregel intrekken',reasonField,f=>mutate('/config/calendar_remove',{id:b.dataset.calendar,reason:f.get('reason')})));
  }
  function peopleSettings() {
    $('settings-body').innerHTML=`<form id="profile-form" class="panel"><h2>HR-medewerkergegevens</h2><p class="muted">Personeelsnummer en afdeling horen bij de vaste interne medewerker-ID. Gebruikersnamen kunnen wijzigen zonder de koppeling te verbreken.</p><div class="form-grid"><label>Medewerker<select name="employee_id" id="profile-employee">${employeeOptions()}</select></label><label>Weergavenaam<input name="name"></label><label>Personeelsnummer<input name="personnel_number"></label><label>Afdeling<input name="department"></label>${reasonField}</div><button>Medewerkergegevens opslaan</button></form>`;
    function fill(){const id=$('profile-employee').value,e=state.employees.find(e=>e.id===id);if(e)for(const name of ['name','personnel_number','department'])document.querySelector(`#profile-form [name=${name}]`).value=e[name]||'';}
    $('profile-employee').onchange=fill;fill();settingsForm('profile-form',f=>mutate('/config/profile',Object.fromEntries(f)));
  }
  function roleSettings() {
    $('settings-body').innerHTML=`<div class="panel"><h2>Gescheiden HR- en technische rechten</h2>${table(['Rol','Uren','Correcties & goedkeuring','Installatie & koppelingen'],['<tr><td>Medewerker</td><td>Eigen uren</td><td>Eigen correctie aanvragen</td><td>Geen toegang</td></tr>','<tr><td>HR</td><td>Alle medewerkers</td><td>Controleren, corrigeren, goedkeuren, afsluiten en exporteren</td><td>Geen toegang</td></tr>','<tr><td>Technisch beheerder</td><td>Eigen uren</td><td>Geen HR-beheer</td><td>Accounts, rollen en verbindingen</td></tr>','<tr><td>Bestaande beheerder (admin)</td><td>Alle uren</td><td>Volledig HR-beheer</td><td>Volledig technisch beheer</td></tr>'])}<p class="note">Technisch beheer wijst rollen toe via Accounts & rechten. De API controleert de actuele rol en blokkeerstatus bij elke beveiligde aanvraag; alleen een menu verbergen geeft geen rechten.</p></div>`;
  }
  function ruleSettings() {
    const r=state.config.rules;
    $('settings-body').innerHTML=`<form id="rules-form" class="panel"><h2>${state.tab==='approval'?'Goedkeuring, export & meldingen':'Berekenings- en registratieregels'}</h2><p class="note warning">Kies een bewuste ingangsdatum. Historisch effect wordt geblokkeerd zodra het goedgekeurde of afgesloten uren raakt. De bestaande automatische STOP blijft standaard acht verstreken uren na START.</p><div class="form-grid">
    <label>Ingangsdatum<input type="date" name="effective_from" value="${dateISO(new Date())}" required></label><label>Tijdzone<input name="timezone" value="${esc(r.timezone)}" required></label>
    <label>Pauzeberekening<select name="break_mode"><option value="recorded" ${r.break_mode==='recorded'?'selected':''}>Werkelijke pauzeregistraties</option><option value="automatic" ${r.break_mode==='automatic'?'selected':''}>Automatische aftrek indien geen pauze geregistreerd</option></select></label><label>Automatische pauze (minuten)<input type="number" name="automatic_break_minutes" min="0" max="720" value="${r.automatic_break_minutes}"></label>
    <label>Aftrek vanaf werktijd (minuten)<input type="number" name="automatic_break_after_minutes" min="1" max="1440" value="${r.automatic_break_after_minutes}"></label><label>Open sessie signaleren na (uren)<input type="number" name="max_open_hours" min="1" max="168" value="${r.max_open_hours}"></label>
    <label>Automatische STOP<select name="auto_stop_mode">${[['legacy_elapsed','Bestaande werking behouden (8 verstreken uren)'],['signal','Alleen signaleren'],['propose','Eindtijd voorstellen ter goedkeuring'],['automatic','Automatisch afsluiten volgens onderstaande regel']].map(([v,l])=>`<option value="${v}" ${r.auto_stop_mode===v?'selected':''}>${l}</option>`).join('')}</select></label>
    <label>Expliciete eindtijdregel<select name="auto_stop_rule"><option value="elapsed" ${r.auto_stop_rule==='elapsed'?'selected':''}>Verstreken uren na START</option><option value="scheduled_end" ${r.auto_stop_rule==='scheduled_end'?'selected':''}>Roostereinde, anders ingestelde eindtijd</option></select></label><label>Verstreken uren<input type="number" name="auto_stop_hours" min="0.25" max="24" step="0.25" value="${r.auto_stop_hours}"></label><label>Ingestelde eindtijd<input type="time" name="auto_stop_at" value="${r.auto_stop_at}"></label>
    <label>Urensaldo signaleren vanaf (minuten; 0 = uit)<input type="number" name="balance_alert_minutes" min="0" max="10080" value="${r.balance_alert_minutes}"></label><label>CSV-scheiding<select name="export_delimiter"><option value=";" ${r.export_delimiter===';'?'selected':''}>Puntkomma</option><option value="," ${r.export_delimiter===','?'selected':''}>Komma</option></select></label>
    <label class="check"><input type="checkbox" name="approval_required" ${r.approval_required?'checked':''}>Goedkeuring opvolgen</label><label class="check"><input type="checkbox" name="allow_approval_with_anomalies" ${r.allow_approval_with_anomalies?'checked':''}>Goedkeuring met gedocumenteerde afwijkingen toestaan</label><label class="check"><input type="checkbox" name="notifications_enabled" ${r.notifications_enabled?'checked':''}>Meldingen in het HR-dashboard tonen</label>${reasonField}</div><button>Regels met ingangsdatum opslaan</button><p class="muted">Urensaldo is geen automatische aanspraak op betaalde overuren. Meldingen verschijnen in de applicatie; er wordt geen e-mail of extern bericht verstuurd.</p></form><div class="panel"><h2>Ingestelde versies</h2>${state.config.policies.map(p=>`<p>${esc(p.effective_from)} · ${esc(p.rules.break_mode)} · ${esc(p.rules.auto_stop_mode)}</p>`).join('')||'<p class="muted">Bestaande instellingen zijn nog van toepassing. Er is geen klantspecifiek rooster aangemaakt.</p>'}</div>`;
    settingsForm('rules-form',f=>{const rules={...r};for(const key of Object.keys(r)){if(['approval_required','allow_approval_with_anomalies','notifications_enabled'].includes(key))rules[key]=f.has(key);else if(typeof r[key]==='number')rules[key]=Number(f.get(key));else rules[key]=f.get(key);}return mutate('/config/policy',{effective_from:f.get('effective_from'),rules,reason:f.get('reason')});});
  }
  async function technical() {
    const data=await api('/system');
    $('content').innerHTML=`<div class="panel"><h2>Installatie en verbindingen</h2><p>Technische instellingen staan los van werkroosters, urencontrole en goedkeuring.</p><p><a href="logs.html">Diagnose en registratietellers</a> · <a href="settings.html">Branding en bestaande instellingen</a> · <a href="user-list.html">Accounts en rollen</a></p></div><div class="panel"><h2>Onderbroken verwerking</h2>${Object.keys(data.pending_ingest).length?table(['Sleutel','Sinds',''],Object.entries(data.pending_ingest).map(([key,p])=>`<tr><td>${esc(key)}</td><td>${esc(when(p.at))}</td><td><button data-reconcile="${esc(key)}">Onderzoeken / vrijgeven</button></td></tr>`)):'<p class="muted">Geen onderbroken verwerkingen bekend.</p>'}</div>`;
    document.querySelectorAll('[data-reconcile]').forEach(b=>b.onclick=()=>modal('Verwerking gecontroleerd afronden',`<p>Gebruik dit alleen na onderzoek van een vastgelopen aanvraag. Een niet-opgeslagen event wordt niet hersteld door deze actie.</p><label class="check"><input name="confirm_lost" type="checkbox">Ontbrekende bronregistratie wordt apart onderzocht</label><label class="check"><input name="confirm_writer_stopped" type="checkbox">Uitvoerende backend is herstart of beëindigd</label>${reasonField}`,f=>mutate('/system/reconcile',{token:b.dataset.reconcile,reason:f.get('reason'),confirm_lost:f.has('confirm_lost'),confirm_writer_stopped:f.has('confirm_writer_stopped')})));
  }
  function fail(error){notice(error.message||'Er is iets misgegaan.',true);}
  function setPeriod() {
    const today=new Date(),start=new Date(today),end=new Date(today);
    if($('period').value==='month'){start.setDate(1);end.setMonth(end.getMonth()+1,0);}
    else if($('period').value==='week'){start.setDate(start.getDate()-((start.getDay()+6)%7));end.setTime(start.getTime());end.setDate(end.getDate()+6);}
    else return;
    $('start').value=dateISO(start);$('end').value=dateISO(end);
  }
  async function init() {
    if(!localStorage.getItem('access_token')){location.href='index.html';return;}
    $('as-of').value=dateISO(new Date());setPeriod();
    state.me=await api('/me');configureNavigation();
    if(!state.me.can_hr)document.querySelector('.eyebrow').textContent=state.me.role==='technical_admin'?'TECHNISCH BEHEER':'MEDEWERKER';
    if(state.me.can_hr){state.employees=await api('/employees');$('employee-filter').innerHTML='<option value="">Alle medewerkers</option>'+state.employees.map(e=>`<option value="${esc(e.id)}">${esc(e.name)}</option>`).join('');
      $('department-filter').innerHTML='<option value="">Alle afdelingen</option>'+[...new Set(state.employees.map(e=>e.department).filter(Boolean))].sort().map(d=>`<option>${esc(d)}</option>`).join('');
      const legacy=new URLSearchParams(location.search).get('legacy_username');if(legacy)state.detail=state.employees.find(e=>e.username===legacy)?.id||null;
    }
    $('logout').onclick=()=>{localStorage.clear();location.href='index.html';};$('refresh').onclick=()=>reload().catch(fail);
    $('period').onchange=setPeriod;$('apply-filters').onclick=()=>{state.page=1;reload().catch(fail);};
    $('cancel').onclick=$('modal-close').onclick=()=>$('modal').close();
    await reload();
  }
  document.addEventListener('DOMContentLoaded',()=>init().catch(fail));
})();
