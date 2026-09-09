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
