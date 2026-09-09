sub while_flow {
  my $value = source();
  while ($condition) {
    # ruleid: flow
    sink($value);
    last;
    sink($value);
  }
}
sub until_flow {
  my $value = source();
  until ($condition) {
    # ruleid: flow
    sink($value);
    last;
  }
}
sub unreachable_loops {
  my $value = source();
  while (0) { sink($value); }
  while ('0') { sink($value); }
  until (1) { sink($value); }
  until ('yes') { sink($value); }
}
sub loop_assignment {
  my $value = 'fixed';
  while ($condition) {
    $value = source();
    last;
  }
  # ruleid: flow
  sink($value);
}
sub skipped_assignment {
  my $value = 'fixed';
  while (0) { $value = source(); }
  sink($value);
}
sub next_skips_sink {
  my $value = source();
  while ($condition) {
    next;
    sink($value);
  }
}
sub conditional_exit {
  while ($condition) {
    last if $done;
    # ruleid: flow
    sink(source());
  }
}
sub block_exit {
  while ($condition) {
    {
      last;
      sink(source());
    }
    # ruleid: flow
    sink(source());
    last;
  }
}
