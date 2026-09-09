class Handler {
  constructor() { this.request = source(); }
  run() {
    this.request = "fixed";
    // ok: typed-constructor
    sink(this.request);
  }
}
const handler = new Handler();
handler.run();
