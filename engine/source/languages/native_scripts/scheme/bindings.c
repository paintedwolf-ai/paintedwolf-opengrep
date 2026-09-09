#include "../bindings.h"
#include <caml/memory.h>

extern const TSLanguage *tree_sitter_scheme(void);

CAMLprim value octs_create_scheme_parser(value unit) {
  CAMLparam1(unit);
  CAMLreturn(octs_create_native_parser(tree_sitter_scheme()));
}
