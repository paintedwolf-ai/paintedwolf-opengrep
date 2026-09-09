module I = IL
module G = AST_generic

let statement s = I.{ s }
let token = G.fake "finally"

let fresh_name prefix =
  I.
    {
      ident = (prefix, token);
      sid = G.SId.mk ();
      id_info = G.empty_id_info ();
      value_origin = None;
    }

let fresh_label () = (("finally", token), G.SId.mk ())
let key ((text, _), sid) = (text, sid)
let same_label left right = key left = key right
let lval name = I.{ base = Var name; rev_offset = [] }
let fetch name = I.{ e = Fetch (lval name); eorig = NoOrig }
let jump label = statement (I.Goto (token, label))
let label value = statement (I.Label value)

let assign name value =
  statement (I.Instr I.{ i = Assign (lval name, value); iorig = NoOrig })

let map_children map stmt =
  let s =
    match stmt.I.s with
    | I.If (tok, condition, yes, no) -> I.If (tok, condition, map yes, map no)
    | I.Loop (tok, condition, body) -> I.Loop (tok, condition, map body)
    | I.Try (body, catches, otherwise, finalizer, complete) ->
        I.Try
          ( map body,
            List.map (fun (name, body) -> (name, map body)) catches,
            map otherwise,
            map finalizer,
            complete )
    | ( I.Instr _ | I.Return _ | I.Goto _ | I.Label _ | I.Throw _ | I.MiscStmt _
      | I.FixmeStmt _ ) as s ->
        s
  in
  statement s

let rec fold_statements visit acc statements =
  List.fold_left
    (fun acc stmt ->
      let acc = visit acc stmt in
      match stmt.I.s with
      | I.If (_, _, yes, no) ->
          fold_statements visit (fold_statements visit acc yes) no
      | I.Loop (_, _, body) -> fold_statements visit acc body
      | I.Try (body, catches, otherwise, finalizer, _) ->
          let acc = fold_statements visit acc body in
          let acc =
            List.fold_left
              (fun acc (_, body) -> fold_statements visit acc body)
              acc catches
          in
          fold_statements visit (fold_statements visit acc otherwise) finalizer
      | _ -> acc)
    acc statements

let labels statements =
  fold_statements
    (fun found stmt ->
      match stmt.I.s with I.Label value -> value :: found | _ -> found)
    [] statements

let statement_count statements =
  fold_statements (fun count _ -> count + 1) 0 statements

let origin statements =
  fold_statements
    (fun found stmt ->
      match found with
      | I.NoOrig -> (
          match stmt.I.s with
          | I.Instr instruction -> instruction.iorig
          | I.Return (_, value) | I.Throw (_, value) -> value.eorig
          | I.If (_, condition, _, _) | I.Loop (_, condition, _) ->
              condition.eorig
          | _ -> I.NoOrig)
      | _ -> found)
    I.NoOrig statements

type budget = { mutable remaining : int; mutable reported : bool }

let expansion_budget = 4096

let clone statements =
  let replacements =
    List.map (fun value -> (value, fresh_label ())) (labels statements)
  in
  let replace value =
    match List.find_opt (fun (old, _) -> same_label old value) replacements with
    | Some (_, replacement) -> replacement
    | None -> value
  in
  let rec walk statements =
    List.map
      (fun stmt ->
        let stmt = map_children walk stmt in
        match stmt.I.s with
        | I.Label value -> label (replace value)
        | I.Goto (tok, value) -> statement (I.Goto (tok, replace value))
        | _ -> stmt)
      statements
  in
  walk statements

let rec normalize_with_budget budget statements =
  List.concat_map (normalize_statement budget) statements

and normalize_statement budget stmt =
  let original = stmt in
  let stmt = map_children (normalize_with_budget budget) stmt in
  match stmt.I.s with
  | I.Try (body, catches, otherwise, (_ :: _ as finalizer), complete) ->
      let protected =
        [ statement (I.Try (body, catches, otherwise, [], complete)) ]
      in
      let internal_labels = labels protected in
      let finished = fresh_label () in
      let return_label = fresh_label () in
      let return_value = fresh_name "_finally_return" in
      let has_return = ref false in
      let redirects = ref 0 in
      let destinations = ref [] in
      let destination original =
        match
          List.find_opt
            (fun (value, _) -> same_label value original)
            !destinations
        with
        | Some (_, replacement) -> replacement
        | None ->
            let replacement = fresh_label () in
            destinations := (original, replacement) :: !destinations;
            replacement
      in
      let rec redirect statements =
        List.concat_map
          (fun stmt ->
            match stmt.I.s with
            | I.Return (tok, value) ->
                has_return := true;
                incr redirects;
                [
                  assign return_value value;
                  statement (I.Goto (tok, return_label));
                ]
            | I.Goto (tok, target)
              when not (List.exists (same_label target) internal_labels) ->
                [ statement (I.Goto (tok, destination target)) ]
            | _ -> [ map_children redirect stmt ])
          statements
      in
      let protected = redirect protected in
      let exception_value = fresh_name "_finally_exception" in
      let exception_label = fresh_label () in
      let copies =
        2 + (if !has_return then 1 else 0) + List.length !destinations
      in
      let growth =
        ((copies - 1) * statement_count finalizer) + !redirects + (copies * 2)
      in
      if growth <= budget.remaining then (
        budget.remaining <- budget.remaining - growth;
        let run completion = clone finalizer @ [ completion ] in
        [
          statement
            (I.Try
               ( protected,
                 [ (exception_value, [ jump exception_label ]) ],
                 [],
                 [],
                 true ));
        ]
        @ run (jump finished)
        @ (if !has_return then
             label return_label
             :: run (statement (I.Return (token, fetch return_value)))
           else [])
        @ label exception_label
          :: run (statement (I.Throw (token, fetch exception_value)))
        @ List.concat_map
            (fun (original, replacement) ->
              label replacement :: run (jump original))
            (List.rev !destinations)
        @ [ label finished ])
      else
        let diagnostic =
          if budget.reported then []
          else (
            budget.reported <- true;
            let source_origin = origin [ original ] in
            [
              statement
                (I.Instr
                   I.
                     {
                       i =
                         CallSpecial
                           (None, (FinallyLimit source_origin, token), []);
                       iorig = NoOrig;
                     });
            ])
        in
        budget.remaining <- 0;
        let shared = fresh_label () in
        let endings =
          (if !has_return then
             [ statement (I.Return (token, fetch return_value)) ]
           else [])
          @ [ statement (I.Throw (token, fetch exception_value)) ]
          @ List.map
              (fun (original, _) -> jump original)
              (List.rev !destinations)
        in
        let dispatch =
          List.fold_right
            (fun completion otherwise ->
              [
                statement
                  (I.If
                     ( token,
                       fetch (fresh_name "_finally_completion"),
                       [ completion ],
                       otherwise ));
              ])
            endings
            [ jump finished ]
        in
        (* Losing completion correlation is conservative: execute one finalizer,
           then retain every possible pending completion, including fallthrough. *)
        diagnostic
        @ [
            statement
              (I.Try
                 ( protected,
                   [ (exception_value, [ jump exception_label ]) ],
                   [],
                   [],
                   true ));
            jump shared;
          ]
        @ (if !has_return then [ label return_label; jump shared ] else [])
        @ [ label exception_label; jump shared ]
        @ List.concat_map
            (fun (_, replacement) -> [ label replacement; jump shared ])
            (List.rev !destinations)
        @ [ label shared ]
        @ finalizer @ dispatch
        @ [ label finished ]
  | _ -> [ stmt ]

let normalize statements =
  normalize_with_budget
    { remaining = expansion_budget; reported = false }
    statements
