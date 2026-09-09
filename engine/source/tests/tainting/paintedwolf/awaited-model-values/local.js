async function run(flag) {
 const db = await openDB();
 // ruleid: flow
 execute(db, source());
}
