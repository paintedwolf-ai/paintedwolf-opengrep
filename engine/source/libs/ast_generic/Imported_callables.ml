(* Reviewed declaration facts and complete typed lookup profiles. *)
open Ppx_hash_lib.Std.Hash.Builtin

type origin = { module_name : string; symbol : string list }
[@@deriving show, eq, ord, hash]

type builtin =
  | String
  | Bool
  | Int
  | Float
  | Number
  | Null
  | Undefined
  | Unit
  | Port
  | Record
[@@deriving show, eq, ord, hash]

type type_ref =
  | Builtin of builtin
  | Union of type_ref list
  | Named of origin * type_ref list
  | Parameter of string
  | Optional of type_ref
  | Metatype of type_ref
  | Function of type_ref list * type_ref
  | Reference of bool * type_ref
  | Existential of origin list
[@@deriving show, eq, ord, hash]

type kind = Operator | FunctionCall | Method | Property
[@@deriving show, eq, ord, hash]

type receiver_mode = Owned | Shared | Mutable [@@deriving show, eq, ord, hash]
type evaluation = Eager | Autoclosure [@@deriving show, eq, ord, hash]
type cardinality = Fixed | Variadic [@@deriving show, eq, ord, hash]

type formal = {
  label : string option;
  typ : type_ref;
  cardinality : cardinality;
  evaluation : evaluation;
}
[@@deriving show, eq, ord, hash]

type generic = { parameter : string; conforms_to : origin list }
[@@deriving show, eq, ord, hash]

type declaration = {
  id : string;
  origin : origin;
  kind : kind;
  owner : type_ref option;
  receiver : receiver_mode option;
  generics : generic list;
  parameters : formal list;
  result : type_ref;
}
[@@deriving show, eq, ord, hash]

type import_mode = All | Module | Selective [@@deriving show, eq, ord, hash]

type selected_symbol = {
  path : string list;
  alias : string option;
  category : string option;
}
[@@deriving show, eq, ord, hash]

type visible_import = {
  imported_module : string;
  import_mode : import_mode;
  import_alias : string option;
  selected : selected_symbol list;
}
[@@deriving show, eq, ord, hash]

type associated_type = { association : origin; value : type_ref }
[@@deriving show, eq, ord, hash]

type type_fact = {
  subject : type_ref;
  conformances : origin list;
  representation : builtin option;
  associated_types : associated_type list;
}
[@@deriving show, eq, ord, hash]

type lookup = {
  lookup_kind : kind;
  name : string;
  lookup_receiver : type_ref option;
  arguments : formal list;
  selected_declaration : string;
}
[@@deriving show, eq, ord, hash]

type type_binding = { spelling : string list; target_type : type_ref }
[@@deriving show, eq, ord, hash]

type profile = {
  visible_imports : visible_import list;
  type_facts : type_fact list;
  type_bindings : type_binding list;
  lookups : lookup list;
}
[@@deriving show, eq, ord, hash]
