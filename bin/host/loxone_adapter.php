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
function sync_api_info($value) {
    // apiKey can contain a single-quoted object literal instead of JSON. Convert
    // string/key tokens only, then use JSON parsing; never execute server text.
    if (is_string($value) && strlen($value)<=20000) {
        $value=preg_replace_callback(<<<'REGEX'
~"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|(?<=[{,])\s*[A-Za-z_][A-Za-z0-9_]*\s*(?=:)~s
REGEX
        ,function($match) {
            $token=$match[0];
            if ($token[0]==='"') return $token;
            if ($token[0]!=="'") return json_encode(trim($token));
            $inner=substr($token,1,-1);$json='"';
            for ($i=0;$i<strlen($inner);$i++) {
                $char=$inner[$i];
                if ($char==='\\') {
                    if (++$i>=strlen($inner)) sync_fail('response_api_info');
                    $escape=$inner[$i];
                    if ($escape==="'") $json.="'";
                    elseif (strpos('"\\/bfnrtu',$escape)!==false) $json.='\\'.$escape;
                    else sync_fail('response_api_info');
                } else $json.=$char==='"'?'\\"':$char;
            }
            $decoded=json_decode($json.'"',true);
            if (json_last_error()!==JSON_ERROR_NONE) sync_fail('response_api_info');
            return json_encode($decoded);
        },$value);
        $value=json_decode($value,true,16);
        if (json_last_error()!==JSON_ERROR_NONE) sync_fail('response_api_info');
    }
    if (!is_array($value) || !is_string($value['version'] ?? null)) sync_fail('response_api_info');
    $serials=[];
    foreach (['mac','snr'] as $field) {
        if (!array_key_exists($field,$value)) continue;
        $serial=$value[$field];
        if (!is_string($serial) || !preg_match('/^(?:[0-9a-f]{12}|(?:[0-9a-f]{2}:){5}[0-9a-f]{2}|(?:[0-9a-f]{2}-){5}[0-9a-f]{2})$/i',$serial)) sync_fail('response_api_info');
        $serials[]=strtoupper(str_replace([':', '-'],'',$serial));
    }
    if (!$serials || count(array_unique($serials))!==1) sync_fail('response_api_info');
    // The key and all other private/unused API attributes stay on the host.
    return ['version'=>$value['version'],'serial'=>$serials[0]];
}
function sync_field_names($value) {
    if (!is_array($value) || array_diff(array_keys($value),array_keys(sync_fields([])))) sync_fail('response_field_names');
    $names=[];
    for ($i=1;$i<=5;$i++) {
        $field='customField'.$i;$label=$value[$field] ?? '';
        if (!is_string($label)) sync_fail('response_field_names');
        $names[$field]=$label!==''?$label:'Custom field '.$i;
    }
    return $names;
}
function sync_user_list($value) {
    if (!is_array($value) || $value!==array_values($value)) sync_fail('response_user_list');
    $seen=[];
    foreach ($value as $user) {
        if (!is_array($user) || !is_string($user['name'] ?? null)) sync_fail('response_user_list');
        try { $uuid=sync_uuid($user['uuid'] ?? null); }
        catch (RuntimeException $e) { sync_fail('response_user_list'); }
        if (isset($seen[strtolower($uuid)])) sync_fail('response_user_list');
        $seen[strtolower($uuid)]=true;
    }
    return $value;
}
function sync_certificate_warning($body, $status) {
    // Only retry a TLS handshake failure: a request with an HTTP response may
    // already have reached the server, so it must never be replayed here.
    if (($body !== null && $body !== false) || (int)($status['code'] ?? -1) !== 0) return null;
    $error=(string)($status['status'] ?? '').' '.(string)($status['message'] ?? '');
    if (preg_match('/no alternative certificate subject name|certificate subject name.*match|certificate.*host ?name.*match/i',$error)) return 'certificate_hostname_mismatch';
    if (preg_match('/certificate.*expired|certificate.*not yet valid/i',$error)) return 'certificate_expired';
    if (preg_match('/SSL certificate problem|self.signed certificate|unable to get.*issuer certificate|unable to verify.*certificate|certificate verify failed|SSL peer certificate.*not OK/i',$error)) return 'certificate_untrusted';
    return null;
}
function sync_sdk_send($slot, $command, $sdk, &$warnings) {
    // Match LoxBerry's local-IP compatibility only after a proven certificate
    // failure. Keep HTTPS; do not retry auth, timeout or uncertain write errors.
    $verify=!$warnings;
    list($body,$status)=$sdk($slot,$command,['timeout'=>5,'ssl_verify_mode'=>$verify?1:0,'ssl_verify_hostname'=>$verify?1:0]);
    if (!is_array($status)) sync_fail('configuration');
    $warning=$verify?sync_certificate_warning($body,$status):null;
    if ($warning) {
        $warnings=[$warning];
        list($body,$status)=$sdk($slot,$command,['timeout'=>5,'ssl_verify_mode'=>0,'ssl_verify_hostname'=>0]);
        if (!is_array($status)) sync_fail('configuration');
    }
    return sync_unwrap($body,(int)($status['code'] ?? 0));
}
function sync_dispatch($request, $environment) {
    if (!is_array($request)) sync_fail('invalid');
    $op=$request['operation'] ?? '';
    $allowed=['miniservers','probe','users','user','patch','resolve'];
    if (!in_array($op,$allowed,true)) sync_fail('invalid');
    $keys=['operation'];
    if ($op!=='miniservers') $keys[]='server';
    if ($op==='user' || $op==='patch') $keys[]='uuid';
    if ($op==='patch') $keys[]='fields';
    if ($op==='resolve') $keys[]='userid';
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
    $send=function($command) use($environment,$slot) {
        try { return $environment['send']($slot,$command); }
        catch (RuntimeException $e) {
            $stages=['/jdev/cfg/apiKey'=>'response_api_info','/jdev/sps/getcustomuserfields'=>'response_field_names','/jdev/sps/getuserlist2'=>'response_user_list'];
            if ($e->getMessage()==='response' && isset($stages[$command])) sync_fail($stages[$command]);
            throw $e;
        }
    };
    $info=sync_api_info($send('/jdev/cfg/apiKey'));
    $version=$info['version'];
    if (!preg_match('/^17\.[0-9]+(?:\.[0-9]+){0,2}$/',$version)) sync_fail('unsupported');
    $serial=$info['serial'];
    if (isset($server['serial']) && $server['serial']!==$serial) sync_fail('identity_changed');
    if ($op==='probe') {
        $names=sync_field_names($send('/jdev/sps/getcustomuserfields'));
        $users=sync_user_list($send('/jdev/sps/getuserlist2'));
        return ['server'=>['slot'=>$slot,'serial'=>$serial],'name'=>(string)$ms['Name'],
            'loxberry_version'=>$config['version'],'miniserver_version'=>$version,'field_names'=>array_intersect_key($names,sync_fields([])),
            'authentication'=>'LoxBerry mshttp_call2 / HTTPS Basic compatibility','user_count'=>count($users)];
    }
    if (!isset($server['serial'])) sync_fail('invalid');
    if ($op==='users') {
        $users=sync_user_list($send('/jdev/sps/getuserlist2'));
        $result=[];
        foreach ($users as $user) {
            if (!is_array($user) || !is_string($user['name'] ?? null)) sync_fail('response');
            $result[]=['uuid'=>sync_uuid($user['uuid'] ?? ''),'name'=>$user['name']];
        }
        return $result;
    }
    if ($op==='resolve') {
        $id=$request['userid'] ?? null;
        if (!is_string($id) || $id==='' || strlen($id)>128 || preg_match('/[\x00-\x1f]/',$id)) sync_fail('invalid');
        if (preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-(?:[0-9a-f]{16}|[0-9a-f]{4}-[0-9a-f]{12})$/i',$id)) {
            $hex=strtolower(str_replace('-','',sync_uuid($id)));
            $uuid=substr($hex,0,8).'-'.substr($hex,8,4).'-'.substr($hex,12,4).'-'.substr($hex,16);
        } else {
            $match=$send('/jdev/sps/checkuserid/'.rawurlencode($id));
            if (!is_array($match) || empty($match['uuid'])) sync_fail('identity_not_found');
            $uuid=sync_uuid($match['uuid']);
        }
        $actual=$send('/jdev/sps/getuser/'.$uuid);
        $actualUuid=sync_uuid($actual['uuid'] ?? null);
        if (strtolower(str_replace('-','',$actualUuid))!==strtolower(str_replace('-','',$uuid))) sync_fail('identity_not_found');
        $safe=sync_user($actual,$actualUuid);
        return ['uuid'=>$safe['uuid'],'name'=>$safe['name'],'source_id'=>$id];
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
        // Firmware uses lastEdit; retain the legacy lowercase spelling too.
        if (in_array($key,['lastedit','lastEdit'],true) || array_key_exists($key,$fields)) continue;
        if (!array_key_exists($key,$after) || $after[$key]!==$value) sync_fail('verification');
    }
    return $safeAfter;
}

function sync_main() {
    ini_set('display_errors','0');ini_set('log_errors','0');ini_set('error_log','/dev/null');
    $warnings=[];
    try {
        $home=getenv('LBHOMEDIR') ?: '/opt/loxberry';
        set_include_path($home.'/libs/phplib'.PATH_SEPARATOR.get_include_path());
        require_once 'loxberry_system.php';require_once 'loxberry_io.php';
        if (!function_exists('mshttp_call2')) sync_fail('configuration');
        $environment=[
            'config'=>function() { return ['version'=>LBSystem::lbversion(),'servers'=>LBSystem::get_miniservers() ?: []]; },
            'send'=>function($slot,$command) use(&$warnings) {
                // Bounded SDK call; never forward raw errors, URI or user objects.
                return sync_sdk_send($slot,$command,'mshttp_call2',$warnings);
            }
        ];
        $request=json_decode(stream_get_contents(STDIN,20000),true,32,JSON_THROW_ON_ERROR);
        $data=sync_dispatch($request,$environment);
        echo json_encode(['ok'=>true,'data'=>$data,'warnings'=>$warnings],JSON_THROW_ON_ERROR)."\n";
    } catch (Throwable $e) {
        $codes=['configuration','tls','authentication','permissions','network','unsupported','identity_changed','identity_not_found','user_missing','response','response_api_info','response_field_names','response_user_list','verification','invalid'];
        $code=in_array($e->getMessage(),$codes,true)?$e->getMessage():'configuration';
        echo json_encode(['ok'=>false,'error'=>$code,'warnings'=>$warnings])."\n";
    }
}
if (PHP_SAPI==='cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '')===__FILE__) sync_main();
