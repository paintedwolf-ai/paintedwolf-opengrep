type selector =
  | Show of AST_generic.tok * AST_generic.ident list
  | Hide of AST_generic.tok * AST_generic.ident list

type t

val unrestricted : t
val module_name : AST_generic.module_name -> string

val attributes :
  selector list ->
  (AST_generic.tok * AST_generic.module_name) list ->
  AST_generic.attribute list

val of_attributes : AST_generic.attribute list -> t
val module_is_fixed : t -> string -> bool
val allows : t -> string -> bool
val selected : selector list -> AST_generic.ident list option

val with_prefix :
  AST_generic.tok ->
  string ->
  AST_generic.attribute list ->
  AST_generic.attribute list

val imported_symbol : t -> string -> string option
