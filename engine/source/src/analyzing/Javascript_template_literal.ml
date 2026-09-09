module G = AST_generic

type segment = { raw : string; cooked : string option; token : Tok.t }
type parts = { segments : segment list; substitutions : G.expr list }

let normalize_lines text =
  let buffer = Buffer.create (String.length text) in
  let rec loop index =
    if index < String.length text then
      if text.[index] = '\r' then (
        Buffer.add_char buffer '\n';
        loop (index + if index + 1 < String.length text && text.[index + 1] = '\n' then 2 else 1))
      else (Buffer.add_char buffer text.[index]; loop (index + 1))
  in
  loop 0;
  Buffer.contents buffer

let hex = function
  | '0' .. '9' as value -> Some (Char.code value - Char.code '0')
  | 'a' .. 'f' as value -> Some (10 + Char.code value - Char.code 'a')
  | 'A' .. 'F' as value -> Some (10 + Char.code value - Char.code 'A')
  | _ -> None

let codepoint buffer value =
  let byte value = Buffer.add_char buffer (Char.chr value) in
  if value < 0x80 then byte value
  else if value < 0x800 then (byte (0xc0 lor (value lsr 6)); byte (0x80 lor (value land 0x3f)))
  else if value < 0x10000 then (
    byte (0xe0 lor (value lsr 12)); byte (0x80 lor ((value lsr 6) land 0x3f));
    byte (0x80 lor (value land 0x3f)))
  else (
    byte (0xf0 lor (value lsr 18)); byte (0x80 lor ((value lsr 12) land 0x3f));
    byte (0x80 lor ((value lsr 6) land 0x3f)); byte (0x80 lor (value land 0x3f)))

let cook raw =
  let length = String.length raw in
  let buffer = Buffer.create length in
  let fixed_hex start count =
    if start + count > length then None
    else
      let rec loop index value =
        if index = start + count then Some value
        else Option.bind (hex raw.[index]) (fun digit -> loop (index + 1) ((value lsl 4) lor digit)) in
      loop start 0
  in
  let unicode start =
    if start < length && raw.[start] = '{' then
      let rec loop index digits value =
        if index >= length || value > 0x10ffff then None
        else if raw.[index] = '}' then
          if digits = 0 then None else Some (value, index + 1)
        else Option.bind (hex raw.[index]) (fun digit -> loop (index + 1) (digits + 1) ((value lsl 4) lor digit)) in
      loop (start + 1) 0 0
    else Option.map (fun value -> (value, start + 4)) (fixed_hex start 4)
  in
  let rec loop index =
    if index = length then Some (Buffer.contents buffer)
    else if raw.[index] <> '\\' then (Buffer.add_char buffer raw.[index]; loop (index + 1))
    else if index + 1 = length then None
    else match raw.[index + 1] with
      | '\n' -> loop (index + 2)
      | '\226' when index + 3 < length && raw.[index + 2] = '\128'
          && (raw.[index + 3] = '\168' || raw.[index + 3] = '\169') -> loop (index + 4)
      | 'b' -> escaped '\b' index
      | 'f' -> escaped '\012' index
      | 'n' -> escaped '\n' index
      | 'r' -> escaped '\r' index
      | 't' -> escaped '\t' index
      | 'v' -> escaped '\011' index
      | '0' when index + 2 = length || raw.[index + 2] < '0' || raw.[index + 2] > '9' -> escaped '\000' index
      | '0' .. '9' -> None
      | 'x' -> Option.bind (fixed_hex (index + 2) 2) (fun value -> codepoint buffer value; loop (index + 4))
      | 'u' -> Option.bind (unicode (index + 2)) (fun (value, next) ->
          if value >= 0xd800 && value <= 0xdbff && next + 6 <= length
              && raw.[next] = '\\' && raw.[next + 1] = 'u' then
            match fixed_hex (next + 2) 4 with
            | Some low when low >= 0xdc00 && low <= 0xdfff ->
                codepoint buffer (0x10000 + ((value - 0xd800) lsl 10) + low - 0xdc00); loop (next + 6)
            | _ -> codepoint buffer value; loop next
          else (codepoint buffer value; loop next))
      | value -> escaped value index
  and escaped value index = Buffer.add_char buffer value; loop (index + 2) in
  loop 0

let parts token arguments =
  let buffer = Buffer.create 32 in
  let start = ref token in
  let segments = ref [] in
  let substitutions = ref [] in
  let flush () =
    let raw = normalize_lines (Buffer.contents buffer) in
    segments := {raw; cooked = cook raw; token = !start} :: !segments;
    Buffer.clear buffer;
    start := token
  in
  List.iter (function
    | G.Arg expression ->
        let interpolation = match expression.G.e_range with
          | Some (location, _) -> String.equal location.Tok.str "${"
          | None -> false in
        (match expression.G.e with
        | G.L (G.String (_, (value, literal_token), _)) when not interpolation ->
            if Buffer.length buffer = 0 then start := literal_token;
            Buffer.add_string buffer value
        | _ -> flush (); substitutions := expression :: !substitutions)
    | _ -> ()) arguments;
  flush ();
  {segments = List.rev !segments; substitutions = List.rev !substitutions}
