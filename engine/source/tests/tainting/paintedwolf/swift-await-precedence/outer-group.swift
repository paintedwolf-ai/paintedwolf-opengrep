func handler() async throws {
 // ruleid: flow
 _ = (await db.raw(input).all())
}
