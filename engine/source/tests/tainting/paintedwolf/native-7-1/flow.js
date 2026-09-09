// ruleid: flow
function handler() { const captured = source(); const read = () => captured; sink(read()); }
