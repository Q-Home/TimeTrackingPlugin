<?php
// The only Miniserver operations exposed to the backend. No web entry point.
function sync_fail($code) { throw new RuntimeException($code); }
function sync_uuid($value) {
    if (!is_string($value) || !preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-(?:[0-9a-f]{16}|[0-9a-f]{4}-[0-9a-f]{12})$/i', $value)) sync_fail('invalid');
    return $value;
}
function sync_fields($user) {
    $fields=[];
    for ($i=1;$i<=5;$i++) $fields['customField'.$i]=(string)($user['customField'.$i] ?? '');
    return $fields;
}
function sync_user($value, $uuid) {
    if (!is_array($value) || ($value['uuid'] ?? '') !== $uuid || !is_string($value['name'] ?? null)) sync_fail('user_missing');
    return ['uuid'=>$uuid,'name'=>$value['name'],'fields'=>sync_fields($value)];
}
function sync_unwrap($body, $http) {
    if ($http==401) sync_fail('authentication');
    if ($http==403) sync_fail('permissions');
    if ($http<200 || $http>=300 || !is_string($body) || strlen($body)>1500000) sync_fail('network');
    $json=json_decode($body,true);
    if (!is_array($json) || !isset($json['LL']) || !is_array($json['LL'])) sync_fail('response');
    $code=(string)($json['LL']['Code'] ?? $json['LL']['code'] ?? '');
    if ($code==='401') sync_fail('authentication');
    if ($code==='403') sync_fail('permissions');
    if ($code!=='200') sync_fail('response');
    if (!array_key_exists('value',$json['LL'])) sync_fail('response');
    $value=$json['LL']['value'];
    if (is_string($value)) {
        $decoded=json_decode($value,true);
        if (json_last_error()===JSON_ERROR_NONE) $value=$decoded;
    }
    return $value;
}
function sync_dispatch($request, $environment) {
    if (!is_array($request)) sync_fail('invalid');
    $op=$request['operation'] ?? '';
    $allowed=['miniservers','probe','users','user','patch'];
    if (!in_array($op,$allowed,true)) sync_fail('invalid');
    $keys=['operation'];
    if ($op!=='miniservers') $keys[]='server';
    if ($op==='user' || $op==='patch') $keys[]='uuid';
    if ($op==='patch') $keys[]='fields';
    if (array_diff(array_keys($request),$keys)) sync_fail('invalid');
    $config=$environment['config']();
    if (version_compare($config['version'],'3.0','<') || version_compare($config['version'],'5.0','>=')) sync_fail('unsupported');
    if ($op==='miniservers') {
        $result=[];
        foreach ($config['servers'] as $slot=>$ms) $result[]=['slot'=>(string)$slot,'name'=>(string)$ms['Name']];
        return ['loxberry_version'=>$config['version'],'servers'=>$result];
    }
    $server=$request['server'] ?? [];$slot=(string)($server['slot'] ?? '');
    if (!preg_match('/^[0-9]{1,4}$/',$slot) || !isset($config['servers'][$slot]) || array_diff(array_keys($server),['slot','serial'])) sync_fail('configuration');
    $ms=$config['servers'][$slot];
    if (strtolower(parse_url($ms['FullURI'] ?? '',PHP_URL_SCHEME) ?? '')!=='https') sync_fail('tls');
    $send=function($command) use($environment,$slot) { return $environment['send']($slot,$command); };
    $info=$send('/jdev/cfg/apiKey');
    if (!is_array($info)) sync_fail('response');
    $version=(string)($info['version'] ?? '');
    if (!preg_match('/^17\.[0-9]+(?:\.[0-9]+){0,2}$/',$version)) sync_fail('unsupported');
    $serial=strtoupper(preg_replace('/[^0-9a-f]/i','',(string)($info['mac'] ?? '')));
    if (strlen($serial)!==12) sync_fail('response');
    if (isset($server['serial']) && $server['serial']!==$serial) sync_fail('identity_changed');
    if ($op==='probe') {
        $names=$send('/jdev/sps/getcustomuserfields');
        if (!is_array($names) || count(array_intersect(array_keys($names),array_keys(sync_fields([]))))!==5) sync_fail('unsupported');
        foreach (array_keys(sync_fields([])) as $key) if (!is_string($names[$key])) sync_fail('response');
        $users=$send('/jdev/sps/getuserlist2');
        if (!is_array($users) || $users!==array_values($users)) sync_fail('response');
        return ['server'=>['slot'=>$slot,'serial'=>$serial],'name'=>(string)$ms['Name'],
            'loxberry_version'=>$config['version'],'miniserver_version'=>$version,'field_names'=>array_intersect_key($names,sync_fields([])),
            'authentication'=>'LoxBerry mshttp_call2 / HTTPS Basic compatibility','user_count'=>count($users)];
    }
    if (!isset($server['serial'])) sync_fail('invalid');
    if ($op==='users') {
        $users=$send('/jdev/sps/getuserlist2');
        if (!is_array($users) || $users!==array_values($users)) sync_fail('response');
        $result=[];
        foreach ($users as $user) {
            if (!is_array($user) || !is_string($user['name'] ?? null)) sync_fail('response');
            $result[]=['uuid'=>sync_uuid($user['uuid'] ?? ''),'name'=>$user['name']];
        }
        return $result;
    }
    $uuid=sync_uuid($request['uuid'] ?? null);
    try { $before=$send('/jdev/sps/getuser/'.$uuid); }
    catch (RuntimeException $e) { if ($e->getMessage()==='response') sync_fail('user_missing'); throw $e; }
    $safe=sync_user($before,$uuid);
    if ($op==='user') return $safe;
    $fields=$request['fields'] ?? null;
    if (!is_array($fields) || !$fields || count($fields)>5) sync_fail('invalid');
    foreach ($fields as $key=>$value) {
        if (!preg_match('/^customField[1-5]$/',$key) || !is_string($value) || strlen($value)>200 || preg_match('/[\x00-\x1f]/',$value)) sync_fail('invalid');
    }
    // All omitted attributes remain untouched on the gated API version. Never
    // replay a complete getuser object, which may overwrite concurrent access edits.
    $payload=['uuid'=>$uuid]+$fields;
    $reply=$send('/jdev/sps/addoredituser/'.rawurlencode(json_encode($payload,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR)));
    if (!is_array($reply) || ($reply['uuid'] ?? null)!==$uuid) sync_fail('response');
    $after=$send('/jdev/sps/getuser/'.$uuid);
    $safeAfter=sync_user($after,$uuid);
    foreach ($fields as $key=>$value) if ($safeAfter['fields'][$key]!==$value) sync_fail('verification');
    // Detect and stop on unexpected server behavior; do not attempt a dangerous
    // full-user rollback that could undo a concurrent administrator's changes.
    foreach ($before as $key=>$value) {
        if ($key==='lastedit' || array_key_exists($key,$fields)) continue;
        if (!array_key_exists($key,$after) || $after[$key]!==$value) sync_fail('verification');
    }
    return $safeAfter;
}

function sync_main() {
    ini_set('display_errors','0');ini_set('log_errors','0');ini_set('error_log','/dev/null');
    try {
        $home=getenv('LBHOMEDIR') ?: '/opt/loxberry';
        set_include_path($home.'/libs/phplib'.PATH_SEPARATOR.get_include_path());
        require_once 'loxberry_system.php';require_once 'loxberry_io.php';
        if (!function_exists('mshttp_call2')) sync_fail('configuration');
        $environment=[
            'config'=>function() { return ['version'=>LBSystem::lbversion(),'servers'=>LBSystem::get_miniservers() ?: []]; },
            'send'=>function($slot,$command) {
                // Bounded SDK call; never forward raw errors, URI or user objects.
                list($body,$status)=mshttp_call2($slot,$command,['timeout'=>5,'ssl_verify_mode'=>1,'ssl_verify_hostname'=>1]);
                return sync_unwrap($body,(int)($status['code'] ?? 0));
            }
        ];
        $request=json_decode(stream_get_contents(STDIN,20000),true,32,JSON_THROW_ON_ERROR);
        $data=sync_dispatch($request,$environment);
        echo json_encode(['ok'=>true,'data'=>$data],JSON_THROW_ON_ERROR)."\n";
    } catch (Throwable $e) {
        $codes=['configuration','tls','authentication','permissions','network','unsupported','identity_changed','user_missing','response','verification','invalid'];
        $code=in_array($e->getMessage(),$codes,true)?$e->getMessage():'configuration';
        echo json_encode(['ok'=>false,'error'=>$code])."\n";
    }
}
if (PHP_SAPI==='cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '')===__FILE__) sync_main();
