#include "../bindings.h"
#include <caml/memory.h>

extern const TSLanguage *tree_sitter_perl(void);

CAMLprim value octs_create_perl_parser(value unit) {
  CAMLparam1(unit);
  CAMLreturn(octs_create_native_parser(tree_sitter_perl()));
}
