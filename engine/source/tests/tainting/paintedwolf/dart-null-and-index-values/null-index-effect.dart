String source() => "untrusted";
void sink(Object? value) {}
void run() {
 Map<String,String>? xs = null;
 String key = "safe";
 xs?[key = source()];
 sink(key);
}
