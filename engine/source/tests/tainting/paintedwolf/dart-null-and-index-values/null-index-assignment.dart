String source() => "untrusted";
void sink(Object? value) {}
class Box { String text = "safe"; }
void run() {
 Map<String,String>? values = null;
 String x = "safe";
 values?[x = source()] = source();
 sink(x);
}
