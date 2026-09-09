function reportError() {
  try {
    external(source());
  } catch (error) {
    if (error && error.code === "ENOENT") console.error(error.message);
    report(error, error.cause);
    throw error;
  }
}
try { reportError(); } catch (error) { console.error(error); }
