String source() => "untrusted";
void sink(Object? value) {}
void run() {
 Map<String,String>? xs = null;
 xs?[source()];

}
