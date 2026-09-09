module Env = Taint_lval_env
module S = Shape_and_sig.Shape

let field target offset =
  {
    target with
    IL.rev_offset =
      Option.value ~default:[] (Taint.rev_IL_offset_of_offset [ offset ])
      @ target.IL.rev_offset;
  }

let reference ~before ~replaced lang env target = function
  | Some source -> Env.copy_reference ~before ~replaced lang env target source
  | None ->
      let _, aliases = Env.prepare_assignment lang env target None in
      Env.finish_assignment env aliases

let is_reference lang env source =
  match Env.find_lval lang env source with
  | Some (S.Cell (_, (S.Scalar _ | S.Callable _))) -> false
  | _ -> true

let rec record ~before ~replaced lang env target expression =
  match expression.IL.e with
  | IL.Fetch source when is_reference lang before source ->
      reference ~before ~replaced lang env target (Some source)
  | IL.RecordOrDict fields ->
      let env = reference ~before ~replaced lang env target None in
      List.fold_left (record_field ~before ~replaced lang target) env fields
  | IL.Composite (IL.CArray, (_, elements, _)) when Lang.is_js lang ->
      let env = reference ~before ~replaced lang env target None in
      let _, env = List.fold_left (fun (index, env) expression ->
        if Taint_array_expression.is_spread expression then
          match expression.IL.e with
          | IL.Fetch source ->
              (match Env.find_lval lang before source with
              | Some (S.Cell (_, (S.Array value | S.TemplateArray value))) ->
                  let env = Shape_and_sig.Fields.fold (fun offset _ env ->
                    match index, offset with
                    | Some base, Taint.Oint element ->
                        let source = field source offset in
                        record ~before ~replaced lang env (field target (Taint.Oint (base + element)))
                          IL.{e = Fetch source; eorig = NoOrig}
                    | _ -> env) value.fields env in
                  (Option.bind index (fun base -> Option.map ((+) base)
                    (Sequence_length.exact_value value.length)), env)
              | _ -> (None, env))
          | _ -> (None, env)
        else match index with
          | Some index -> (Some (index + 1), record ~before ~replaced lang env
              (field target (Taint.Oint index)) expression)
          | None -> (None, env)) (Some 0, env) elements in
      env
  | IL.Composite ((IL.CArray | IL.CList | IL.CTuple), (_, elements, _)) ->
      let env = reference ~before ~replaced lang env target None in
      List.mapi (fun index value -> (index, value)) elements
      |> List.fold_left
           (fun env (index, value) ->
             record ~before ~replaced lang env
               (field target (Taint.Oint index))
               value)
           env
  | _ -> reference ~before ~replaced lang env target None

and record_field ~before ~replaced lang target env = function
  | IL.Field (name, value) ->
      record ~before ~replaced lang env (field target (Taint.Ofld name)) value
  | IL.Entry (key, value) ->
      let offset =
        Taint.offset_of_IL lang { IL.o = IL.Index key; oorig = IL.NoOrig }
      in
      if offset = Taint.Oany then reference ~before ~replaced lang env target None
      else record ~before ~replaced lang env (field target offset) value
  | IL.Spread { e = IL.Fetch source; _ } -> (
      match Env.find_lval lang before source with
      | Some (S.Cell (_, (S.Instance (_, fields) | S.Obj fields | (S.TemplateArray {fields; _} | S.Array {fields; _})))) ->
          Shape_and_sig.Fields.fold
            (fun offset _ env ->
              let source = field source offset in
              if offset = Taint.Oany then
                reference ~before ~replaced lang env target None
              else
                reference ~before ~replaced lang env (field target offset)
                  (if is_reference lang before source then Some source else None))
            fields env
      | _ -> reference ~before ~replaced lang env target None)
  | IL.Spread _ -> reference ~before ~replaced lang env target None

let assignment ~before lang env target expression =
  match expression.IL.e with
  | IL.RecordOrDict _
  | IL.Composite ((IL.CArray | IL.CList | IL.CTuple), _) ->
      record ~before ~replaced:target lang env target expression
  | _ -> env
