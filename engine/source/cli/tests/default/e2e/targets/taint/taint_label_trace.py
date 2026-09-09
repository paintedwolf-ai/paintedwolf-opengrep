context = source_b()
value = source_a(context)
# ruleid: conjunction
sink_and(value)
# ruleid: disjunction
sink_or(value)
# ruleid: negative
sink_negative(context)
# ruleid: nested
sink_nested(value)

# ok: conjunction
sink_and(context)
# ok: disjunction
sink_or(context)
# ok: nested
sink_nested(context)
# ok: disjunction
sink_or(source_a("constant"))
# ok: negative
sink_negative(source_d())
