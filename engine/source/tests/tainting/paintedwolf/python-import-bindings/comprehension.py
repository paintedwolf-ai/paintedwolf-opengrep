from trusted import source
# ok: binding
values = [source() for source in factories]
# ruleid: binding
source()
