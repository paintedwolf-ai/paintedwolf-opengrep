let is_spread (expression : IL.exp) =
  match IL.any_of_value_orig expression.eorig with
  | AST_generic.E {e = AST_generic.Call
      ({e = AST_generic.IdSpecial (AST_generic.Spread, _); _}, _); _} -> true
  | _ -> false

