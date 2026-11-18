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
// Test the actual SDK boundary, including the reported local-IP TLS failure.
$success='{"LL":{"Code":"200","value":{"safe":true}}}';
$warnings=[];$calls=[];
$sdk=function($slot,$command,$options) use(&$calls,$success) {$calls[]=$options;return [$success,['code'=>200]];};
check(sync_sdk_send('1','/jdev/cfg/apiKey',$sdk,$warnings)['safe']===true);
check(count($calls)===1 && $calls[0]['ssl_verify_hostname']===1 && !$warnings);
foreach ([
    'SSL: no alternative certificate subject name matches target host name 192.0.2.10'=>'certificate_hostname_mismatch',
    'SSL certificate problem: self-signed certificate'=>'certificate_untrusted',
    'SSL certificate problem: unable to get local issuer certificate'=>'certificate_untrusted',
    'SSL certificate problem: certificate has expired'=>'certificate_expired',
    'SSL certificate problem: certificate is not yet valid'=>'certificate_expired',
] as $error=>$warning) {
    $warnings=[];$calls=[];
    $sdk=function($slot,$command,$options) use(&$calls,$success,$error) {
        $calls[]=$options;
        return $options['ssl_verify_mode']?[null,['code'=>0,'status'=>$error]]:[$success,['code'=>200]];
    };
    check(sync_sdk_send('1','/jdev/cfg/apiKey',$sdk,$warnings)['safe']===true);
    check(count($calls)===2 && $calls[0]['ssl_verify_mode']===1 && $calls[1]['ssl_verify_mode']===0 && $calls[1]['ssl_verify_hostname']===0);
    check($warnings===[$warning]);
    sync_sdk_send('1','/jdev/sps/getcustomuserfields',$sdk,$warnings);
    check(count($calls)===3 && $calls[2]['ssl_verify_mode']===0); // cached only inside this request
    check(strpos(json_encode($warnings),'192.0.2.10')===false);
}
foreach ([0=>'Connection timed out',401=>'Unauthorized',403=>'Forbidden',500=>'Server error'] as $code=>$error) {
    $warnings=[];$calls=[];
    $sdk=function($slot,$command,$options) use(&$calls,$code,$error) {$calls[]=$options;return [null,['code'=>$code,'status'=>$error]];};
    fails($code===401?'authentication':($code===403?'permissions':'network'),function() use($sdk,&$warnings){sync_sdk_send('1','/jdev/sps/addoredituser/payload',$sdk,$warnings);});
    check(count($calls)===1 && !$warnings);
}
foreach ([401=>'authentication',403=>'permissions',0=>'network'] as $code=>$expected) {
    $warnings=[];$calls=[];
    $sdk=function($slot,$command,$options) use(&$calls,$code) {
        $calls[]=$options;
        return $options['ssl_verify_mode']?[null,['code'=>0,'status'=>'SSL certificate problem: self-signed certificate']]:[null,['code'=>$code,'status'=>'Synthetic failure']];
    };
    fails($expected,function() use($sdk,&$warnings){sync_sdk_send('1','/jdev/cfg/apiKey',$sdk,$warnings);});
    check(count($calls)===2 && $warnings===['certificate_untrusted']);
}
check(sync_certificate_warning($success,['code'=>200,'status'=>'SSL certificate problem'])===null);
check(sync_certificate_warning(null,['code'=>500,'status'=>'SSL certificate problem'])===null);
// A new RPC verifies again and clears warnings after a certificate is repaired.
$warnings=[];$calls=[];
$sdk=function($slot,$command,$options) use(&$calls,$success) {$calls[]=$options;return [$success,['code'=>200]];};
sync_sdk_send('1','/jdev/cfg/apiKey',$sdk,$warnings);
check($calls[0]['ssl_verify_mode']===1 && !$warnings);
// Full probe and verified partial write still work via certificate compatibility.
$warnings=[];$sdkCalls=[];
$sdk=function($slot,$command,$options) use(&$sdkCalls,$env) {
    $sdkCalls[]=$options;
    if ($options['ssl_verify_mode']) return [null,['code'=>0,'status'=>'SSL: no alternative certificate subject name matches target host name 192.0.2.10']];
    return [json_encode(['LL'=>['Code'=>'200','value'=>$env['send']($slot,$command)]]),['code'=>200]];
};
$compatible=$env;$compatible['send']=function($slot,$command) use($sdk,&$warnings){return sync_sdk_send($slot,$command,$sdk,$warnings);};
check(sync_dispatch(['operation'=>'probe','server'=>$server],$compatible)['server']['serial']===$serial);
check(count($sdkCalls)===4 && count($warnings)===1);
$result=sync_dispatch(['operation'=>'patch','server'=>$server,'uuid'=>$uuid,'fields'=>['customField1'=>'8u 00m']],$compatible);
check($result['fields']['customField1']==='8u 00m');
foreach (['password','userRights','usergroups','nfcTags','keycodes','validFrom','validUntil','customField2','name','uuid'] as $key) check($user[$key]===$original[$key]);
// apiKey uses a single-quoted literal on real firmware, with snr rather than mac.
$literal="{'snr':'AABBCCDDEEFF','version':'17.0.7.14','key':'SYNTHETIC_PRIVATE','httpsStatus':2,'local':true}";
$formats=[
    $literal,
    "{snr: 'aa:bb:cc:dd:ee:ff', version: '17.0.7.14', local: false}",
    '{"snr":"AABBCCDDEEFF","version":"17.0.7.14"}',
    ['version'=>'17.0.7.14','mac'=>'AA-BB-CC-DD-EE-FF'],
    ['version'=>'17.0.7.14','mac'=>'AABBCCDDEEFF','snr'=>'aabbccddeeff'],
];
foreach ($formats as $format) {
    $info=sync_api_info($format);
    check($info===['version'=>'17.0.7.14','serial'=>'AABBCCDDEEFF']);
    check(strpos(json_encode($info),'SYNTHETIC_PRIVATE')===false);
}
$escaped=<<<'LITERAL'
{'version':'17.0.7.14','snr':'AABBCCDDEEFF','name':'D\'Example "Unit"','path':'C:\\test','unicode':'\u00e9'}
LITERAL;
check(sync_api_info($escaped)['serial']===$serial);
foreach (["{'version':'17.0','snr':'AABBCCDDEEFF'}; system('SYNTHETIC_PRIVATE')", "{'version':'17.0','snr':function(){}}", "{'version':'17.0','snr':'bad'}", 'not an object',
    ['version'=>'17.0','mac'=>'AABBCCDDEEFF','snr'=>'112233445566'],['version'=>'17.0'],['snr'=>$serial],str_repeat('x',20001)] as $bad) {
    fails('response_api_info',function() use($bad){sync_api_info($bad);});
}
check(count(sync_field_names([]))===5);
check(sync_field_names([])['customField1']==='Custom field 1');
check(sync_field_names(['customField3'=>'Persoonlijk label'])['customField3']==='Persoonlijk label');
check(sync_field_names(['customField1'=>''])['customField1']==='Custom field 1');
fails('response_field_names',function(){sync_field_names(['other'=>'not a custom field']);});
fails('response_field_names',function(){sync_field_names(['customField1'=>['not a label']]);});
check(sync_user_list([])===[]);
fails('response_user_list',function(){sync_user_list(['users'=>[]]);});
fails('response_user_list',function(){sync_user_list([['uuid'=>'bad','name'=>'Synthetic']]);});
fails('response_user_list',function() use($uuid){sync_user_list([['uuid'=>$uuid,'name'=>'A'],['uuid'=>$uuid,'name'=>'B']]);});
$observed=$env;
$observed['send']=function($slot,$command) use($literal) {
    if ($command==='/jdev/cfg/apiKey') return sync_unwrap(json_encode(['LL'=>['Code'=>'200','value'=>$literal]]),200);
    if ($command==='/jdev/sps/getcustomuserfields' || $command==='/jdev/sps/getuserlist2') return sync_unwrap('{"LL":{"Code":"200","value":"[]"}}',200);
    throw new Exception('Unexpected command');
};
$probe=sync_dispatch(['operation'=>'probe','server'=>['slot'=>'1']],$observed);
check($probe['server']['serial']===$serial && $probe['user_count']===0 && count($probe['field_names'])===5);
check(strpos(json_encode($probe),'SYNTHETIC_PRIVATE')===false);
$bad=$env;$bad['send']=function(){sync_fail('response');};
fails('response_api_info',function() use($bad){sync_dispatch(['operation'=>'probe','server'=>['slot'=>'1']],$bad);});
echo 'Host adapter: '.$count." assertions passed; no network used.\n";
