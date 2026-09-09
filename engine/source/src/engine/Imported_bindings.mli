type t

val of_program : ?lang:Lang.t -> AST_generic.program -> t

val matches :
  t ->
  AST_generic.expr ->
  ?symbol:string list ->
  ?imports:Rule.import_model ->
  string list ->
  bool

val unbound : AST_generic.expr -> bool
