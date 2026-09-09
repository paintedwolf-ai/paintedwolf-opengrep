my ($dirty, $clean) = (source(), 'fixed');
# ruleid: flow
sink($dirty);
sink($clean);
my ($first, $second) = ('fixed', source());
sink($first);
# ruleid: flow
sink($second);
my ($ignored, undef, $last) = ('fixed', source(), 'fixed');
sink($ignored);
sink($last);
my $outer = source();
{
  my ($outer, $other) = ('fixed', source());
  sink($outer);
  # ruleid: flow
  sink($other);
}
# ruleid: flow
sink($outer);
my ($copy, $unused) = ($outer, 'fixed');
# ruleid: flow
sink($copy);
sink($unused);
my ($one, $two);
sink($one);
sink($two);
{
  my ($outer, $empty);
  sink($outer);
}
# ruleid: flow
sink($outer);
my ($available, $absent) = (source(),);
# ruleid: flow
sink($available);
sink($absent);
my ($only) = (source(), 'unused');
# ruleid: flow
sink($only);
sub declaration_arguments {
  # ruleid: flow
  sink(my $input = source());
  # ruleid: flow
  sink($input);
  sink(my $fixed = 'constant');
  sink($fixed);
  sink(my $uninitialized);
}
