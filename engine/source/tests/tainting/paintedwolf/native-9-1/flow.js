function handler() { const captured = source(); let read = () => captured; read = () => "fixed"; sink(read()); }
