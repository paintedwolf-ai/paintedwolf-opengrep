func handler() {
 // ruleid: raw-interpolation
 sink("SELECT \(raw: value)")
 sink("SELECT \(bind: value)")
 sink("SELECT \(literal: value)")
 sink("SELECT \(ident: value)")
}
