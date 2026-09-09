open IL

let node receiver node =
  match receiver with
  | None -> node
  | Some receiver ->
      let rec expression value =
        match value.e with
        | Fetch target -> {value with e = Fetch (lval target)}
        | _ -> snd (IL_helpers.fold_map_children (fun () value -> ((), expression value)) () value)
      and lval target =
        let offsets = List.map (fun offset ->
          match offset.o with
          | Index value -> {offset with o = Index (expression value)}
          | Dot _ | Slice _ -> offset) target.rev_offset in
        match target.base with
        | VarSpecial (This, _) ->
            {receiver with rev_offset = offsets @ receiver.rev_offset}
        | Mem value -> {base = Mem (expression value); rev_offset = offsets}
        | Var _ | VarSpecial _ -> {target with rev_offset = offsets}
      in
      let argument = function
        | Unnamed value -> Unnamed (expression value)
        | Named (name, value) -> Named (name, expression value)
        | KeywordSpread value -> KeywordSpread (expression value) in
      let instruction value =
        let i = match value.i with
          | Assign (target, value) -> Assign (lval target, expression value)
          | AssignAnon (target, entity) -> AssignAnon (lval target, entity)
          | Call (target, callee, args) ->
              Call (Option.map lval target, expression callee, List.map argument args)
          | CallSpecial (target, kind, args) ->
              CallSpecial (Option.map lval target, kind, List.map argument args)
          | New (target, kind, constructor, args) ->
              New (lval target, kind, Option.map expression constructor, List.map argument args)
          | FixmeInstr _ as original -> original in
        {value with i} in
      let n = match node.n with
        | NInstr value -> NInstr (instruction value)
        | TrueNode value -> TrueNode (expression value)
        | FalseNode value -> FalseNode (expression value)
        | NCond (token, value) -> NCond (token, expression value)
        | NReturn (token, value) -> NReturn (token, expression value)
        | NThrow (token, value) -> NThrow (token, expression value)
        | Enter | Exit | Join | NGoto _ | NOther _ | NTodo _ as original -> original in
      {node with n}
