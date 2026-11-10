(() => {
  'use strict';
  const $=id=>document.getElementById(id);let me;
  function notice(message,error=false){const div=document.createElement('div');div.className='notice'+(error?' error':'');div.textContent=message;$('feedback').replaceChildren(div);}
  async function api(path,options={}){
    const response=await fetch('/api/v1'+path,{cache:'no-store',...options,headers:{Authorization:'Bearer '+(localStorage.getItem('access_token')||''),...options.headers}});
    if(response.status===401){location.href='index.html';throw Error('Meld opnieuw aan.');}
    const body=await response.json();if(!response.ok)throw Error(body.error||body.message||'De wijziging kon niet worden opgeslagen.');return body;
  }
  async function init(){
    $('logout').onclick=()=>{localStorage.clear();location.href='index.html';};
    if(!localStorage.getItem('access_token')){location.href='index.html';return;}
    try{me=(await api('/hr/me')).data;$('identity').textContent=me.username;$('account-name').textContent='Aangemeld als '+me.username;$('save-password').disabled=false;}
    catch(error){notice(error.message,true);return;}
    $('password-form').onsubmit=async event=>{
      event.preventDefault();const button=$('save-password'),form=new FormData(event.target);
      const password=form.get('password');
      if(password!==form.get('repeat_password')){notice('De nieuwe wachtwoorden komen niet overeen.',true);return;}
      if(new TextEncoder().encode(password).length>72){notice('Het nieuwe wachtwoord is te lang. Gebruik maximaal 72 UTF-8 bytes; bijzondere tekens kunnen meer dan één byte innemen.',true);return;}
      button.disabled=true;
      try{await api('/users/'+encodeURIComponent(me.id)+'/password',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:form.get('current_password'),password})});event.target.reset();notice('Je wachtwoord is gewijzigd. Gebruik het nieuwe wachtwoord bij je volgende aanmelding.');}
      catch(error){notice(error.message,true);}finally{button.disabled=false;}
    };
  }
  document.addEventListener('DOMContentLoaded',init);
})();
