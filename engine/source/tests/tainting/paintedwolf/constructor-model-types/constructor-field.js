class Handler {
  constructor() { this.request = source(); }
  run() {
    // ruleid: typed-constructor
    sink(this.request);
  }
}
const handler = new Handler();
handler.run();
