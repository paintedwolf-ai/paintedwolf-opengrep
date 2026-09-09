async function run(flag) {
 const db = flag ? await openDB() : {};
 execute(db, source());
}
