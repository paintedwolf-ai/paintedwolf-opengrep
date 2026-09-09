String identity(String value) { return value }
// ruleid: flow
sink(identity(source()))
sink(identity("safe"))
String constant(String value) { return "safe" }
sink(constant(source()))
