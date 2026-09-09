// ruleid: flow
function handler() { const captured = source(); const read = () => captured; const alias = read; sink(alias()); }
