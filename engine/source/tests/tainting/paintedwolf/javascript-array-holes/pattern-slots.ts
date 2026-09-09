// ok: single, leading, trailing
observe([,]);
// ruleid: single
observe([undefined]);
// ruleid: single
observe([1,]);
// ruleid: leading
observe([,1]);
// ruleid: leading
observe([,1,]);
// ruleid: trailing
observe([1,,]);
// ok: single, leading, trailing
observe([,,]);
// ok: single, leading, trailing
observe([]);
