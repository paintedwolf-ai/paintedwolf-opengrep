String source() => "untrusted";
void sink(Object? value) {}
class Box {
 Box get next => this;
 void send(Object? value) {}
}
Box? unknownBox() => null;
void run() {
 Map<String,Box>? xs = null;
 String x = "safe";
 xs?["x"]?.send(x = source());
 sink(x);
}
