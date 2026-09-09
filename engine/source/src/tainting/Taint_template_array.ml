module S = Shape_and_sig.Shape
module Fields = Shape_and_sig.Fields
module Env = Taint_lval_env

let create cooked raw =
  match cooked, raw with
  | S.Array cooked, S.Array raw ->
      let raw = S.Cell (`Clean, S.TemplateArray raw) in
      S.TemplateArray {cooked with fields = Fields.add (Taint.Ostr "raw") raw cooked.fields}
  | _ -> S.Bot

let immutable_target lang env (target : IL.lval) =
  match target.rev_offset with
  | [] -> false
  | _ :: parent ->
      match Env.find_lval lang env {target with rev_offset = parent} with
      | Some (S.Cell (_, S.TemplateArray _)) -> true
      | _ -> false

let immutable_effect env var offset =
  let rec walk shape offset =
    match shape, offset with
    | S.TemplateArray _, _ -> true
    | _, [] -> false
    | _, first :: remaining ->
        match Taint_shape.find_in_shape_poly ~taints:Taint.Taint_set.empty [first] shape with
        | Some (_, nested) -> walk nested remaining
        | None -> false in
  match Env.find_var env var with
  | Some (S.Cell (_, shape)) -> walk shape offset
  | None -> false

let check_instruction lang env (instruction : IL.instr) =
  let target = match instruction.i with
    | IL.CallSpecial (_, (IL.DeleteProperty, _), [IL.Unnamed {e = IL.Fetch target; _}]) -> Some target
    | _ -> IL_helpers.lval_of_instr_opt instruction in
  match target with
  | Some target when immutable_target lang env target ->
      Taint_model_types.immutable_template_write instruction.iorig;
      true
  | _ -> false

let rejects_method lang env (callee : IL.exp) =
  let mutates = function
    | "copyWithin" | "fill" | "pop" | "push" | "reverse" | "shift"
    | "sort" | "splice" | "unshift" -> true
    | _ -> false in
  if not (Lang.is_js lang) then false
  else match callee.e with
    | IL.Fetch ({rev_offset = method_offset :: parent; _} as target) ->
        let method_name =
          match Taint.offset_of_rev_IL_offset lang ~rev_offset:[method_offset] with
          | [Taint.Ofld name] -> Some (fst name.IL.ident)
          | [Taint.Ostr name] -> Some name
          | _ -> None in
        (match method_name, Env.find_lval lang env {target with rev_offset = parent} with
        | Some name, Some (S.Cell (_, S.TemplateArray {fields; _})) when mutates name ->
            not (Fields.exists (fun offset _ -> match offset with
              | Taint.Ostr field -> String.equal name field
              | Taint.Ofld field -> String.equal name (fst field.IL.ident)
              | _ -> false) fields)
        | _ -> false)
    | _ -> false
