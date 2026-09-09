async function run(flag) {
 const data = {db: await openDB()};
 // ruleid: flow
 execute(data.db, source());
}
