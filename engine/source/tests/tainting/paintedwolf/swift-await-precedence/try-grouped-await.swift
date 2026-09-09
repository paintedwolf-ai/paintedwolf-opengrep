func handler() async throws {
 _ = try (await db.raw(input)).all()
}
