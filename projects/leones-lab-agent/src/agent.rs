use crate::detect;
use crate::inventory;
use crate::output::json::{self, Value};
use crate::system;
use std::collections::BTreeMap;
use std::io::{Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::time::Duration;

const MAX_RESPONSE_BYTES: usize = 8 * 1024 * 1024;
const MAX_TOOL_ROUNDS: usize = 4;

fn string(value: &str) -> Value {
    Value::String(value.to_string())
}

fn object(entries: &[(&str, Value)]) -> Value {
    let mut map = BTreeMap::new();
    for (key, value) in entries {
        map.insert((*key).to_string(), (*value).clone());
    }
    Value::Object(map)
}

fn array(values: Vec<Value>) -> Value {
    Value::Array(values)
}

fn system_json() -> String {
    let info = system::collect();
    let value = object(&[
        ("schema_version", Value::Number("1".to_string())),
        ("os", string(&info.os)),
        ("kernel", string(&info.kernel)),
        ("cpu", string(&info.cpu)),
        ("logical_cpus", Value::Number(info.logical_cpus.to_string())),
        ("memory_total_kib", info.memory_total_kib.map(|v| Value::Number(v.to_string())).unwrap_or(Value::Null)),
        ("memory_available_kib", info.memory_available_kib.map(|v| Value::Number(v.to_string())).unwrap_or(Value::Null)),
        ("gpu", string(&info.gpu)),
        ("cuda_toolkit", string(&info.cuda)),
    ]);
    json::stringify(&value)
}

fn tools_json() -> String {
    let tools = detect::TOOLS.iter().filter_map(|name| {
        detect::find_executable(name).map(|path| {
            object(&[
                ("name", string(name)),
                ("path", string(&path.display().to_string())),
            ])
        })
    }).collect();
    json::stringify(&array(tools))
}

fn function_tool(name: &str, description: &str) -> Value {
    object(&[
        ("type", string("function")),
        ("function", object(&[
            ("name", string(name)),
            ("description", string(description)),
            ("parameters", object(&[
                ("type", string("object")),
                ("properties", object(&[])),
                ("additionalProperties", Value::Bool(false)),
            ])),
        ])),
    ])
}

fn tool_definitions() -> Value {
    array(vec![
        function_tool("get_system_info", "Obtiene información de solo lectura del sistema operativo, CPU, RAM, GPU y CUDA Toolkit."),
        function_tool("get_local_inventory", "Obtiene el inventario local de herramientas, cachés de modelos y componentes ODS/Magnitude."),
        function_tool("get_detected_tools", "Lista ejecutables detectados y sus rutas. No confirma que estén ejecutándose."),
    ])
}

fn endpoint_parts(endpoint: &str) -> Result<(String, u16, String), String> {
    let rest = endpoint.strip_prefix("http://")
        .ok_or_else(|| "Solo se permiten endpoints HTTP locales; HTTPS y hosts remotos están deshabilitados.".to_string())?;
    let (authority, path) = match rest.find('/') {
        Some(index) => (&rest[..index], &rest[index..]),
        None => (rest, "/v1/chat/completions"),
    };
    if authority.contains('@') || path.contains('\r') || path.contains('\n') || path.chars().any(char::is_whitespace) {
        return Err("Endpoint inválido.".to_string());
    }
    let (host, port) = match authority.rsplit_once(':') {
        Some((host, port)) => (host, port.parse::<u16>().map_err(|_| "Puerto HTTP inválido.".to_string())?),
        None => (authority, 80),
    };
    if !matches!(host, "127.0.0.1" | "localhost") {
        return Err("Por seguridad, el agente solo conecta con 127.0.0.1 o localhost.".to_string());
    }
    if path.is_empty() || !path.starts_with('/') {
        return Err("Ruta HTTP inválida.".to_string());
    }
    Ok((host.to_string(), port, path.to_string()))
}

fn find_header_end(bytes: &[u8]) -> Option<usize> {
    bytes.windows(4).position(|window| window == b"\r\n\r\n")
}

fn decode_chunked(input: &[u8]) -> Result<Vec<u8>, String> {
    let mut output = Vec::new();
    let mut cursor = 0usize;
    loop {
        let line_end = input.get(cursor..)
            .and_then(|rest| rest.windows(2).position(|w| w == b"\r\n"))
            .map(|offset| cursor + offset)
            .ok_or_else(|| "Respuesta HTTP chunked truncada.".to_string())?;
        let line = std::str::from_utf8(&input[cursor..line_end])
            .map_err(|_| "Cabecera de chunk inválida.".to_string())?;
        let size_text = line.split(';').next().unwrap_or("").trim();
        let size = usize::from_str_radix(size_text, 16)
            .map_err(|_| "Tamaño de chunk inválido.".to_string())?;
        cursor = line_end + 2;
        if size == 0 {
            return Ok(output);
        }
        let end = cursor.checked_add(size).ok_or_else(|| "Tamaño de respuesta excesivo.".to_string())?;
        let chunk = input.get(cursor..end).ok_or_else(|| "Chunk HTTP incompleto.".to_string())?;
        output.extend_from_slice(chunk);
        if output.len() > MAX_RESPONSE_BYTES {
            return Err("La respuesta HTTP supera el límite de 8 MiB.".to_string());
        }
        if input.get(end..end + 2) != Some(&b"\r\n"[..]) {
            return Err("Separador de chunk inválido.".to_string());
        }
        cursor = end + 2;
    }
}

fn http_post(endpoint: &str, payload: &str) -> Result<String, String> {
    let (host, port, path) = endpoint_parts(endpoint)?;
    let addresses = (host.as_str(), port).to_socket_addrs()
        .map_err(|e| format!("No se pudo resolver el endpoint local: {e}"))?;
    let mut stream = None;
    let mut last_error = None;
    for address in addresses {
        match TcpStream::connect_timeout(&address, Duration::from_secs(3)) {
            Ok(connection) => { stream = Some(connection); break; }
            Err(error) => last_error = Some(error),
        }
    }
    let mut stream = stream.ok_or_else(|| {
        format!("No se pudo conectar al modelo local: {}", last_error.map(|e| e.to_string()).unwrap_or_else(|| "sin direcciones".to_string()))
    })?;
    stream.set_read_timeout(Some(Duration::from_secs(180)))
        .map_err(|e| format!("No se pudo configurar timeout: {e}"))?;
    stream.set_write_timeout(Some(Duration::from_secs(15)))
        .map_err(|e| format!("No se pudo configurar timeout: {e}"))?;

    let request = format!(
        "POST {path} HTTP/1.1\r\nHost: {host}:{port}\r\nContent-Type: application/json\r\nAccept: application/json\r\nAccept-Encoding: identity\r\nConnection: close\r\nContent-Length: {}\r\n\r\n{}",
        payload.len(), payload
    );
    stream.write_all(request.as_bytes())
        .map_err(|e| format!("Error enviando petición al modelo local: {e}"))?;
    let mut response = Vec::new();
    stream.take(MAX_RESPONSE_BYTES as u64).read_to_end(&mut response)
        .map_err(|e| format!("Error leyendo respuesta del modelo local: {e}"))?;
    let header_end = find_header_end(&response)
        .ok_or_else(|| "Respuesta HTTP sin separador de cabeceras.".to_string())?;
    if header_end > 64 * 1024 {
        return Err("Cabeceras HTTP demasiado grandes.".to_string());
    }
    let headers = std::str::from_utf8(&response[..header_end])
        .map_err(|_| "Cabeceras HTTP no válidas.".to_string())?;
    let status = headers.lines().next().and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse::<u16>().ok())
        .ok_or_else(|| "Estado HTTP inválido.".to_string())?;
    let body_bytes = &response[header_end + 4..];
    let chunked = headers.lines().any(|line| {
        line.split_once(':').map(|(key, value)| {
            key.eq_ignore_ascii_case("transfer-encoding") && value.to_ascii_lowercase().contains("chunked")
        }).unwrap_or(false)
    });
    let body = if chunked {
        decode_chunked(body_bytes)?
    } else {
        let content_length = headers.lines().find_map(|line| {
            let (key, value) = line.split_once(':')?;
            if key.eq_ignore_ascii_case("content-length") {
                value.trim().parse::<usize>().ok()
            } else { None }
        });
        if let Some(length) = content_length {
            if length > MAX_RESPONSE_BYTES || body_bytes.len() < length {
                return Err("Longitud de respuesta HTTP inválida o incompleta.".to_string());
            }
            body_bytes[..length].to_vec()
        } else {
            body_bytes.to_vec()
        }
    };
    let body_text = String::from_utf8(body).map_err(|_| "El modelo local devolvió una respuesta que no es UTF-8.".to_string())?;
    if !(200..300).contains(&status) {
        return Err(format!("El endpoint local respondió HTTP {status}: {}", body_text.chars().take(1000).collect::<String>()));
    }
    Ok(body_text)
}

fn tool_result(name: &str, arguments: &str) -> Result<String, String> {
    let parsed = json::parse(arguments)?;
    match parsed {
        Value::Object(ref values) if values.is_empty() => {}
        _ => return Err("Esta herramienta no acepta argumentos.".to_string()),
    }
    match name {
        "get_system_info" => Ok(system_json()),
        "get_local_inventory" => Ok(inventory::to_json(&inventory::collect())),
        "get_detected_tools" => Ok(tools_json()),
        _ => Err(format!("Herramienta no permitida: {name}")),
    }
}

fn request_payload(model: &str, messages: &[Value]) -> String {
    let request = object(&[
        ("model", string(model)),
        ("messages", array(messages.to_vec())),
        ("tools", tool_definitions()),
        ("tool_choice", string("auto")),
        ("stream", Value::Bool(false)),
    ]);
    json::stringify(&request)
}

pub fn ask(endpoint: &str, model: &str, prompt: &str) -> Result<String, String> {
    if model.trim().is_empty() || prompt.trim().is_empty() {
        return Err("Debes indicar un modelo y una pregunta.".to_string());
    }
    endpoint_parts(endpoint)?;
    if prompt.len() > 64 * 1024 {
        return Err("La pregunta supera el límite de 64 KiB.".to_string());
    }
    let system_prompt = "Eres LEONES Lab Agent, un asistente de laboratorio local. Responde en el idioma del usuario. Usa las herramientas disponibles cuando necesites datos reales del equipo. No inventes inventario, hardware ni resultados. Solo puedes consultar información; no ejecutes comandos arbitrarios, no instales, descargues, cargues ni elimines modelos y no cambies servicios. Distingue siempre descubrimiento, presencia de pesos, disponibilidad, carga, ejecución y benchmark medido.";
    let mut messages = vec![
        object(&[("role", string("system")), ("content", string(system_prompt))]),
        object(&[("role", string("user")), ("content", string(prompt))]),
    ];

    for round in 0..=MAX_TOOL_ROUNDS {
        let payload = request_payload(model, &messages);
        let response_text = http_post(endpoint, &payload)?;
        let response = json::parse(&response_text)
            .map_err(|e| format!("La respuesta del modelo no es JSON válido: {e}"))?;
        let message = response.get("choices")
            .and_then(Value::as_array)
            .and_then(|choices| choices.first())
            .and_then(|choice| choice.get("message"))
            .ok_or_else(|| "La respuesta no contiene choices[0].message.".to_string())?;
        let calls = message.get("tool_calls").and_then(Value::as_array);
        let Some(calls) = calls.filter(|calls| !calls.is_empty()) else {
            return match message.get("content") {
                Some(Value::String(content)) => Ok(content.clone()),
                Some(Value::Null) | None => Ok("El modelo devolvió una respuesta vacía.".to_string()),
                Some(other) => Ok(json::stringify(other)),
            };
        };
        if round == MAX_TOOL_ROUNDS {
            return Err("Se alcanzó el límite de llamadas a herramientas.".to_string());
        }
        messages.push((*message).clone());
        for call in calls {
            let call_id = call.get("id").and_then(Value::as_str)
                .ok_or_else(|| "La llamada de herramienta no contiene id.".to_string())?;
            let function = call.get("function")
                .ok_or_else(|| "La llamada de herramienta no contiene function.".to_string())?;
            let name = function.get("name").and_then(Value::as_str)
                .ok_or_else(|| "La llamada de herramienta no contiene nombre.".to_string())?;
            let arguments = match function.get("arguments") {
                Some(Value::String(raw)) => raw.clone(),
                Some(value) => json::stringify(value),
                None => "{}".to_string(),
            };
            let result = tool_result(name, &arguments)
                .unwrap_or_else(|error| format!("{{\"error\":{}}}", json::escape(&error)));
            messages.push(object(&[
                ("role", string("tool")),
                ("tool_call_id", string(call_id)),
                ("content", string(&result)),
            ]));
        }
    }
    Err("El agente terminó sin respuesta final.".to_string())
}


#[cfg(test)]
mod tests {
    use super::endpoint_parts;

    #[test]
    fn accepts_loopback_http_endpoint() {
        let parsed = endpoint_parts("http://127.0.0.1:8080/v1/chat/completions").unwrap();
        assert_eq!(parsed, ("127.0.0.1".to_string(), 8080, "/v1/chat/completions".to_string()));
    }

    #[test]
    fn rejects_remote_and_https_endpoints() {
        assert!(endpoint_parts("https://127.0.0.1:8080/v1/chat/completions").is_err());
        assert!(endpoint_parts("http://example.com/v1/chat/completions").is_err());
    }
}


#[cfg(test)]
mod http_tests {
    use super::decode_chunked;

    #[test]
    fn decodes_chunked_http_body() {
        let decoded = decode_chunked(b"4\r\nWiki\r\n5\r\npedia\r\n0\r\n\r\n").unwrap();
        assert_eq!(decoded, b"Wikipedia");
    }

    #[test]
    fn rejects_invalid_chunk_size() {
        assert!(decode_chunked(b"z\r\nx\r\n0\r\n\r\n").is_err());
    }
}


#[cfg(test)]
mod permission_tests {
    use super::tool_result;

    #[test]
    fn refuses_arbitrary_tools() {
        assert!(tool_result("run_shell", "{}").is_err());
    }

    #[test]
    fn refuses_tool_arguments() {
        assert!(tool_result("get_system_info", r#"{"command":"id"}"#).is_err());
    }
}
