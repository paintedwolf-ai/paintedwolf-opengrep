func handler() async throws {
 _ = (await db.raw(input)).all()
}
