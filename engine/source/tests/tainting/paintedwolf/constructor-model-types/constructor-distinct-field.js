class Handler {
  constructor() { this.request = source(); this.other = "fixed"; }
  run() {
    // ok: typed-constructor
    sink(this.other);
  }
}
const handler = new Handler();
handler.run();
