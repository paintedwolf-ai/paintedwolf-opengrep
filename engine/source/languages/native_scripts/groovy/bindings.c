#include "../bindings.h"
#include <caml/memory.h>

extern const TSLanguage *tree_sitter_groovy(void);

CAMLprim value octs_create_groovy_parser(value unit) {
  CAMLparam1(unit);
  CAMLreturn(octs_create_native_parser(tree_sitter_groovy()));
}
