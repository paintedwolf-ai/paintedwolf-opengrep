let fresh lang params env =
  Fold_IL_params.fold
    (fun env id info _ ->
      let variable = AST_to_IL.var_of_id_info id info in
      let parameter = IL_helpers.lval_of_var variable in
      let writing, aliases =
        Taint_lval_env.prepare_assignment lang env parameter None
      in
      Taint_lval_env.finish_assignment
        (Taint_lval_env.clean lang writing parameter) aliases
      |> Taint_lval_env.clear_call_value variable)
    env params
