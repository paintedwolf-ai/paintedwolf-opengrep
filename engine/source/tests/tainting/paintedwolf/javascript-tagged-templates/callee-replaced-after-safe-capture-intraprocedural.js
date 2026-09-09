let tag=(strings,value)=>"fixed";
// ok: flow
sink(tag`${(tag=(strings,value)=>value,source())}`);
