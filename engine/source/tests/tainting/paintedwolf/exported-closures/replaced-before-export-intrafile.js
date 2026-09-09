// ok: flow
let plugin = async (app) => { sink(source()); };
plugin = async (app) => { sink("fixed"); };
export { plugin };
