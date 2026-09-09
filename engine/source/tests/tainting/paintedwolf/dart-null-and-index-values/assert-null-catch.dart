String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = null;
 try { x!; sink(source()); } catch (_) {
 // ruleid: flow
 sink(source());
 }
}
