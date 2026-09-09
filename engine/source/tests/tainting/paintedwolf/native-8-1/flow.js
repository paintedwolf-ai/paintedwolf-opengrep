function handler() { let captured = source(); const read = () => captured; captured = "fixed"; sink(read()); }
