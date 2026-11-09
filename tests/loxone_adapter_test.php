<?php
// Synthetic fixture only. This file never loads the LoxBerry SDK or a network.
require_once __DIR__.'/../bin/host/loxone_adapter.php';
$count=0;
function check($condition) { global $count; $count++; if (!$condition) throw new Exception('Assertion '.$count.' failed'); }
function fails($code,$callback) { try { $callback(); } catch (RuntimeException $e) { check($e->getMessage()===$code); return; } throw new Exception('Expected '.$code); }
$uuid='12345678-1234-1234-1234567890abcdef';
$serial='AABBCCDDEEFF';
$user=['uuid'=>$uuid,'name'=>'synthetic.employee','password'=>'SYNTHETIC_PRIVATE',
    'userRights'=>2047,'usergroups'=>[['uuid'=>'group-1']], 'nfcTags'=>[['id'=>'SYNTHETIC_TAG']],
    'keycodes'=>[['code'=>'SYNTHETIC_CODE']],'validFrom'=>12,'validUntil'=>34,
    'customField1'=>'old hours','customField2'=>'other application','lastedit'=>1];
$original=$user;$commands=[];
$config=['version'=>'3.0.1.0','servers'=>['1'=>['Name'=>'Synthetic server','FullURI'=>'https://synthetic:SYNTHETIC_PRIVATE@example.invalid']]];
$env=['config'=>function() use(&$config){return $config;},'send'=>function($slot,$command) use(&$user,&$commands,$serial,$uuid) {
    $commands[]=$command;
    if ($command==='/jdev/cfg/apiKey') return ['version'=>'17.0.1.0','mac'=>'AA:BB:CC:DD:EE:FF'];
    if ($command==='/jdev/sps/getcustomuserfields') return ['customField1'=>'Hours','customField2'=>'Keep','customField3'=>'Three','customField4'=>'Four','customField5'=>'Five'];
    if ($command==='/jdev/sps/getuserlist2') return [['uuid'=>$uuid,'name'=>'synthetic.employee']];
    if ($command==='/jdev/sps/getuser/'.$uuid) return $user;
    if (strpos($command,'/jdev/sps/addoredituser/')===0) {
        $payload=json_decode(rawurldecode(substr($command,strlen('/jdev/sps/addoredituser/'))),true);
        check(array_keys($payload)===['uuid','customField1']);
        $user=array_replace($user,$payload);$user['lastedit']=2;return $user;
    }
    throw new Exception('Unexpected command');
}];
$server=['slot'=>'1','serial'=>$serial];
$result=sync_dispatch(['operation'=>'miniservers'],$env);
check(strpos(json_encode($result),'SYNTHETIC_PRIVATE')===false);
$probe=sync_dispatch(['operation'=>'probe','server'=>['slot'=>'1']],$env);
check($probe['server']['serial']===$serial);
$result=sync_dispatch(['operation'=>'user','server'=>$server,'uuid'=>$uuid],$env);
check(array_keys($result)===['uuid','name','fields']);
check(strpos(json_encode($result),'SYNTHETIC_PRIVATE')===false);
sync_dispatch(['operation'=>'patch','server'=>$server,'uuid'=>$uuid,'fields'=>['customField1'=>'7u 15m']],$env);
check($user['customField1']==='7u 15m');
foreach (['password','userRights','usergroups','nfcTags','keycodes','validFrom','validUntil','customField2','name','uuid'] as $key) check($user[$key]===$original[$key]);
$before=count($commands);
fails('invalid',function() use($env){sync_dispatch(['operation'=>'execute','command'=>'deleteuser'],$env);});
check(count($commands)===$before);
fails('invalid',function() use($env,$server,$uuid){sync_dispatch(['operation'=>'patch','server'=>$server,'uuid'=>$uuid,'fields'=>['userRights'=>0]],$env);});
fails('invalid',function() use($env,$server){sync_dispatch(['operation'=>'patch','server'=>$server,'uuid'=>'','fields'=>['customField1'=>'x']],$env);});
fails('identity_changed',function() use($env){sync_dispatch(['operation'=>'users','server'=>['slot'=>'1','serial'=>'112233445566']],$env);});
$old=$config;$config['servers']['1']['FullURI']='http://example.invalid';
fails('tls',function() use($env,$server){sync_dispatch(['operation'=>'probe','server'=>$server],$env);});$config=$old;
$config['version']='2.2';fails('unsupported',function() use($env){sync_dispatch(['operation'=>'miniservers'],$env);});$config=$old;
$config['version']='4.0.0.14';check(count(sync_dispatch(['operation'=>'miniservers'],$env)['servers'])===1);$config=$old;
foreach ([401=>'authentication',403=>'permissions',500=>'network'] as $status=>$code) fails($code,function() use($status){sync_unwrap('{}',$status);});
fails('permissions',function(){sync_unwrap('{"LL":{"Code":"403","value":"secret error"}}',200);});
fails('response',function(){sync_unwrap('{"LL":{"Code":"500","value":"private failure"}}',200);});
fails('response',function(){sync_unwrap('{"LL":{"Code":"200"}}',200);});
check(sync_unwrap('{"LL":{"Code":"200","value":"{\"name\":\"safe\"}"}}',200)['name']==='safe');
$bad=$env;$bad['send']=function($slot,$command) {return ['version'=>'16.0.1.0','mac'=>'AA:BB:CC:DD:EE:FF'];};
fails('unsupported',function() use($bad,$server){sync_dispatch(['operation'=>'probe','server'=>$server],$bad);});
$bad=$env;$bad['send']=function($slot,$command) use($uuid) {if ($command==='/jdev/cfg/apiKey')return ['version'=>'17.0.1.0','mac'=>'AA:BB:CC:DD:EE:FF'];sync_fail('response');};
fails('user_missing',function() use($bad,$server,$uuid){sync_dispatch(['operation'=>'user','server'=>$server,'uuid'=>$uuid],$bad);});
echo 'Host adapter: '.$count." assertions passed; no network used.\n";
