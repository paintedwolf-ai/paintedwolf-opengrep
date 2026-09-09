const module = shared();
module.run = value => "fixed";
const independent = factory(module);
// ruleid: model-flow
independent.run(source());
const next = shared();
next.run(source());
const fresh = factory(null);
unknownMutation(next);
// ruleid: model-flow
fresh.run(source());
const mixed = condition ? next : fresh;
mixed.run(source());
